import os
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from PIL import Image
import imagehash

EXTENSOES_VALIDAS: Set[str] = {'.jpg', '.jpeg', '.png', '.webp', '.heic'}


def carregar_imagens_do_diretorio(
    caminho_dir: str
) -> Tuple[Optional[List[Path]], Optional[Dict[str, List[Path]]]]:
    """Varre um diretório e calcula o hash perceptual de cada imagem encontrada.

    Entradas (Parâmetros):
        caminho_dir (str): String com o caminho relativo ou absoluto do diretório
            a ser analisado.

    Saídas (Retornos):
        Tuple[Optional[List[Path]], Optional[Dict[str, List[Path]]]]:
            - Posição 0: Lista contendo objetos Path de todos os arquivos de imagem válidos.
            - Posição 1: Dicionário onde a chave é o hash perceptual (str) e o valor é uma lista
              de objetos Path de imagens com aquele mesmo hash.
            - Retorna (None, None) caso a pasta informada não exista ou seja inválida.

    Fluxo da Função:
        1. Converte a string do caminho recebida para um objeto Path.
        2. Valida a existência e se o caminho é um diretório com .exists() e .is_dir().
        3. Realiza uma busca recursiva com .rglob('*') em todas as subpastas.
        4. Filtra arquivos testando a extensão em EXTENSOES_VALIDAS.
        5. Abre a imagem em modo de contexto seguro (with Image.open).
        6. Calcula o hash perceptual (imagehash.phash) e converte para string hexadecimal.
        7. Agrupa o caminho do arquivo no dicionário mapa_imagens usando .setdefault().

    """
    mapa_imagens: Dict[str, List[Path]] = {}
    caminho: Path = Path(caminho_dir)

    if not caminho.exists() or not caminho.is_dir():
        print(f"Erro: O diretório '{caminho_dir}' não existe.")
        return None, None

    print(f"Analisando arquivos em: {caminho_dir}...")

    lista_arquivos: List[Path] = []
    for arquivo in caminho.rglob('*'):
        if arquivo.suffix.lower() in EXTENSOES_VALIDAS:
            lista_arquivos.append(arquivo)
            try:
                with Image.open(arquivo) as img:
                    h: str = str(imagehash.phash(img))
                    mapa_imagens.setdefault(h, []).append(arquivo)
            except Exception as e:
                print(f"Aviso: Não foi possível ler a imagem {arquivo.name}: {e}")

    return lista_arquivos, mapa_imagens


def prioridade_nome_original(caminho: Path) -> Tuple[int, int, str]:
    """Gera uma chave de ordenação multinível para priorizar a foto original em detrimento de suas cópias.

    Entradas (Parâmetros):
        caminho (Path): Objeto Path representando o caminho do arquivo de imagem a ser avaliado.

    Saídas (Retornos):
        Tuple[int, int, str]: Tupla contendo 3 critérios sequenciais de comparação para ordenação:
            - Posição 0 (int): 0 se for original (sem termos como 'copy', 'copia'), 1 se for cópia.
            - Posição 1 (int): Tamanho do nome do arquivo (len(caminho.stem)).
            - Posição 2 (str): Nome do arquivo em letras minúsculas para desempate alfabético.

    Fluxo da Função:
        1. Extrai o nome do arquivo sem extensão e converte para letras minúsculas com caminho.stem.lower().
        2. Verifica se algum termo indicador de cópia ('copy', 'copia', 'cópia', 'duplicate') está presente.
        3. Monta e retorna a tupla multinível (0 ou 1, tamanho, nome).

    """
    nome_lower: str = caminho.stem.lower()
    tem_termo_copia: bool = any(termo in nome_lower for termo in ['copy', 'copia', 'cópia', 'duplicate'])

    return (1 if tem_termo_copia else 0, len(nome_lower), nome_lower)


def mover_duplicadas_para_lixeira(duplicadas_dict: Dict[str, List[Path]], pasta_lixeira: str) -> None:
    """Move apenas as fotos duplicadas/excedentes de cada grupo para a pasta de lixeira de forma segura.

    Entradas (Parâmetros):
        duplicadas_dict (Dict[str, List[Path]]): Dicionário onde a chave é o hash perceptual
            e o valor é a lista de objetos Path com imagens idênticas.
        pasta_lixeira (str): String com o caminho do diretório de destino para a lixeira.

    Saídas (Retornos):
        None: A função realiza alterações diretamente no sistema de arquivos e exibe relatórios no console.

    Fluxo da Função:
        1. Cria/valida o diretório da lixeira utilizando path_lixeira.mkdir(parents=True, exist_ok=True).
        2. Itera sobre cada grupo do dicionário de duplicadas.
        3. Ordena a lista de arquivos com sorted() usando a chave prioridade_nome_original.
        4. Mantém a foto do índice [0] no álbum original e seleciona as demais ([1:]) para mover.
        5. Para cada cópia, monta o caminho de destino e verifica colisões de nomes usando enquanto destino.exists().
        6. Renomeia com sufixos numéricos sequenciais (_1, _2) se o arquivo já existir na lixeira.
        7. Executa a movimentação com shutil.move() e exibe o log de movimentação no console.

   """
    path_lixeira: Path = Path(pasta_lixeira)
    path_lixeira.mkdir(parents=True, exist_ok=True)

    total_movidas: int = 0
    print(f"\nMovendo duplicadas para: {path_lixeira.resolve()}")

    for hash_str, caminhos in duplicadas_dict.items():
        caminhos_ordenados: List[Path] = sorted(caminhos, key=prioridade_nome_original)

        original: Path = caminhos_ordenados[0]
        copias: List[Path] = caminhos_ordenados[1:]

        print(f"  [MANTIDA NO ÁLBUM] {original.name}")

        for copia in copias:
            try:
                destino: Path = path_lixeira / copia.name
                contador: int = 1

                while destino.exists():
                    destino = path_lixeira / f"{copia.stem}_{contador}{copia.suffix}"
                    contador += 1

                shutil.move(str(copia), str(destino))
                print(f"  [MOVIDO PARA LIXEIRA] {copia.name} -> {destino.name}")
                total_movidas += 1
            except Exception as e:
                print(f"  [ERRO] Não foi possível mover {copia.name}: {e}")

    print(f"\nConcluído: {total_movidas} arquivo(s) duplicado(s) movidos para a lixeira.")


def comparar_e_gerenciar_albuns(
    pasta_galeria_geral: str,
    pasta_album_alvo: str,
    pasta_lixeira: str
) -> None:
    """Orquestra a leitura, comparação lógica entre diretórios e a remoção interativa de duplicadas.

    Entradas (Parâmetros):
        pasta_galeria_geral (str): String com o caminho do diretório da Galeria Geral de fotos.
        pasta_album_alvo (str): String com o caminho do diretório do Álbum Específico a ser comparado.
        pasta_lixeira (str): String com o caminho da pasta de Lixeira para onde enviar arquivos excedentes.

    Saídas (Retornos):
        None: A função exibe o relatório de comparação no console e solicita entrada do usuário via terminal (input).

    Fluxo da Função:
        1. Invoca carregar_imagens_do_diretorio para a Galeria Geral e extrai o dicionário de hashes.
        2. Invoca carregar_imagens_do_diretorio para o Álbum Específico e extrai o dicionário de hashes.
        3. Interrompe a execução com return antecipado se qualquer um dos diretórios for inválido.
        4. Extrai os conjuntos de chaves (set(hashes.keys())) de ambos os locais.
        5. Identifica duplicadas DENTRO do Álbum Específico via dictionary comprehension (len(caminhos) > 1).
        6. Calcula a interseção de conjuntos (set_hashes_geral.intersection(set_hashes_album)) para fotos em ambos os locais.
        7. Calcula a diferença de conjuntos (set_hashes_geral - set_hashes_album) para fotos que estão apenas na Galeria Geral.
        8. Imprime o relatório formatado das 3 categorias no terminal.
        9. Se existirem duplicadas internas no álbum, solicita confirmação do usuário (input()) para mover para a lixeira.
        10. Caso confirmado ('s'), invoca a função mover_duplicadas_para_lixeira.

    """
    arquivos_geral, hashes_geral = carregar_imagens_do_diretorio(pasta_galeria_geral)
    if hashes_geral is None:
        return

    arquivos_album, hashes_album = carregar_imagens_do_diretorio(pasta_album_alvo)
    if hashes_album is None:
        return

    set_hashes_geral: Set[str] = set(hashes_geral.keys())
    set_hashes_album: Set[str] = set(hashes_album.keys())

    print("\n" + "=" * 50)
    print(" RESULTADO DA ANÁLISE")
    print("=" * 50)

    duplicadas_no_album: Dict[str, List[Path]] = {
        h: caminhos for h, caminhos in hashes_album.items() if len(caminhos) > 1
    }
    print(f"\n1. Duplicadas DENTRO do Álbum Específico ({len(duplicadas_no_album)} grupo(s)):")
    if duplicadas_no_album:
        for h, caminhos in duplicadas_no_album.items():
            print("   - Grupo de fotos idênticas:")
            for c in caminhos:
                print(f"     * {c.name}")
    else:
        print("   Nenhuma foto duplicada encontrada no álbum.")

    estao_no_album: Set[str] = set_hashes_geral.intersection(set_hashes_album)
    print(f"\n2. Fotos da Galeria Geral que JÁ ESTÃO no Álbum ({len(estao_no_album)}):")
    for h in estao_no_album:
        exemplo_geral: str = hashes_geral[h][0].name
        exemplo_album: str = hashes_album[h][0].name
        print(f"   - {exemplo_geral} (no álbum como: {exemplo_album})")

    nao_estao_no_album: Set[str] = set_hashes_geral - set_hashes_album
    print(f"\n3. Fotos da Galeria Geral que NÃO ESTÃO no Álbum ({len(nao_estao_no_album)}):")
    for h in nao_estao_no_album:
        for caminho in hashes_geral[h]:
            print(f"   - {caminho.name}")

    if duplicadas_no_album:
        resposta: str = input("\nDeseja mover as fotos duplicadas do álbum para a lixeira? (s/n): ").strip().lower()
        if resposta == 's':
            mover_duplicadas_para_lixeira(duplicadas_no_album, pasta_lixeira)


if __name__ == "__main__":
    print("--- Comparador e Gerenciador de Álbuns ---\n")

    caminho_geral: str = input("Digite o caminho da GALERIA GERAL: ").strip()
    caminho_album: str = input("Digite o caminho do ÁLBUM ESPECÍFICO: ").strip()
    caminho_lixeira: str = input("Digite o caminho para a PASTA DE LIXEIRA: ").strip()

    comparar_e_gerenciar_albuns(caminho_geral, caminho_album, caminho_lixeira)
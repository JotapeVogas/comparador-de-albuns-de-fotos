import os
import shutil
from pathlib import Path
from PIL import Image
import imagehash

# Extensões de imagem suportadas
EXTENSOES_VALIDAS = {'.jpg', '.jpeg', '.png', '.webp', '.heic'}


def carregar_imagens_do_diretorio(caminho_dir):
    """Lê todas as imagens do diretório e calcula seus hashes perceptuais."""
    mapa_imagens = {}  # {hash: [lista_de_caminhos]}
    caminho = Path(caminho_dir)

    if not caminho.exists() or not caminho.is_dir():
        print(f"Erro: O diretório '{caminho_dir}' não existe.")
        return None, None

    print(f"Analisando arquivos em: {caminho_dir}...")

    lista_arquivos = []
    for arquivo in caminho.rglob('*'):
        if arquivo.suffix.lower() in EXTENSOES_VALIDAS:
            lista_arquivos.append(arquivo)
            try:
                with Image.open(arquivo) as img:
                    h = str(imagehash.phash(img))
                    mapa_imagens.setdefault(h, []).append(arquivo)
            except Exception as e:
                print(f"Aviso: Não foi possível ler a imagem {arquivo.name}: {e}")

    return lista_arquivos, mapa_imagens


def mover_duplicadas_para_lixeira(duplicadas_dict, pasta_lixeira):
    """Move as cópias excedentes para a pasta de lixeira, mantendo a primeira foto de cada grupo."""
    path_lixeira = Path(pasta_lixeira)
    path_lixeira.mkdir(parents=True, exist_ok=True)

    total_movidas = 0
    print(f"\nMovendo duplicadas para: {path_lixeira.resolve()}")

    for h, caminhos in duplicadas_dict.items():
        # Mantém o primeiro arquivo da lista e move todos os outros
        original = caminhos[0]
        copias = caminhos[1:]

        for copia in copias:
            try:
                # Evita sobrescrever arquivos com o mesmo nome na lixeira
                destino = path_lixeira / copia.name
                contador = 1
                while destino.exists():
                    destino = path_lixeira / f"{copia.stem}_{contador}{copia.suffix}"
                    contador += 1

                shutil.move(str(copia), str(destino))
                print(f"  [MOVIDO] {copia.name} -> {destino.name}")
                total_movidas += 1
            except Exception as e:
                print(f"  [ERRO] Não foi possível mover {copia.name}: {e}")

    print(f"\nConcluído: {total_movidas} arquivo(s) duplicado(s) movidos para a lixeira.")


def comparar_e_gerenciar_albuns(pasta_galeria_geral, pasta_album_alvo, pasta_lixeira):
    # 1. Carrega imagens da Galeria Geral
    arquivos_geral, hashes_geral = carregar_imagens_do_diretorio(pasta_galeria_geral)
    if hashes_geral is None:
        return

    # 2. Carrega imagens do Álbum Específico
    arquivos_album, hashes_album = carregar_imagens_do_diretorio(pasta_album_alvo)
    if hashes_album is None:
        return

    set_hashes_geral = set(hashes_geral.keys())
    set_hashes_album = set(hashes_album.keys())

    print("\n" + "=" * 50)
    print(" RESULTADO DA ANÁLISE")
    print("=" * 50)

    # A. Fotos repetidas DENTRO do álbum específico
    duplicadas_no_album = {h: caminhos for h, caminhos in hashes_album.items() if len(caminhos) > 1}
    print(f"\n1. Duplicadas DENTRO do Álbum Específico ({len(duplicadas_no_album)} grupo(s)):")
    if duplicadas_no_album:
        for h, caminhos in duplicadas_no_album.items():
            print("   - Grupo de fotos idênticas:")
            for c in caminhos:
                print(f"     * {c.name}")
    else:
        print("   Nenhuma foto duplicada encontrada no álbum.")

    # B. Fotos que ESTÃO na galeria geral E TAMBÉM no álbum específico
    estao_no_album = set_hashes_geral.intersection(set_hashes_album)
    print(f"\n2. Fotos da Galeria Geral que JÁ ESTÃO no Álbum ({len(estao_no_album)}):")
    for h in estao_no_album:
        exemplo_geral = hashes_geral[h][0].name
        exemplo_album = hashes_album[h][0].name
        print(f"   - {exemplo_geral} (no álbum como: {exemplo_album})")

    # C. Fotos da Galeria Geral que NÃO ESTÃO no álbum específico
    nao_estao_no_album = set_hashes_geral - set_hashes_album
    print(f"\n3. Fotos da Galeria Geral que NÃO ESTÃO no Álbum ({len(nao_estao_no_album)}):")
    for h in nao_estao_no_album:
        for caminho in hashes_geral[h]:
            print(f"   - {caminho.name}")

    # D. Opção para mover duplicadas do álbum para a lixeira
    if duplicadas_no_album:
        resposta = input("\nDeseja mover as fotos duplicadas do álbum para a lixeira? (s/n): ").strip().lower()
        if resposta == 's':
            mover_duplicadas_para_lixeira(duplicadas_no_album, pasta_lixeira)


if __name__ == "__main__":
    print("--- Comparador e Gerenciador de Álbuns ---\n")

    caminho_geral = input("Digite o caminho da GALERIA GERAL: ").strip()
    caminho_album = input("Digite o caminho do ÁLBUM ESPECÍFICO: ").strip()
    caminho_lixeira = input("Digite o caminho para a PASTA DE LIXEIRA (ex: /sdcard/Pictures/Lixeira): ").strip()

    comparar_e_gerenciar_albuns(caminho_geral, caminho_album, caminho_lixeira)
import sys
import math
import time
import signal
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import ephem
import RPi.GPIO as GPIO

SRC_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SRC_DIR.parent
ASSETS_DIR = PROJECT_DIR / "assets"

if str(PROJECT_DIR / "library") not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR / "library"))

import GC9A01 # Display driver for GC9A01

LARGURA = 240 # width of the display in pixels
ALTURA = 240 # height of the display in pixels
TIMEZONE = "America/Sao_Paulo" # your local timezone, e.g., "America/New_York" or "Europe/London"
CICLO_LUNAR = 29.53 # average length of the lunar cycle in days
TOTAL_IMAGENS = 238 # total number of moon phase images, extracted from NASA's website (included in repository)
LATITUDE = -25.563 # your location's latitude
LONGITUDE = -51.486 # your location's longitude

BOTAO_GPIO = 17 # GPIO pin number for the button
TEMPO_PRESSAO_LONGA = 5.0 # seconds to consider a long press to shutdown the Raspberry Pi
INTERVALO_LOOP = 0.05 # seconds between each iteration of the main loop
INTERVALO_TELA_IMAGEM = 120 # seconds to update the moon image
INTERVALO_TELA_INFO = 30 # seconds to update the moon information

TELA_IMAGEM = 0
TELA_INFO = 1

tela_atual = TELA_IMAGEM
disp = None


def inicializar_display():
    disp = GC9A01.GC9A01(
        port=0,
        cs=0,
        dc=22,
        backlight=None,
        rst=27,
        width=240,
        height=240,
        rotation=180, # Display roatated 180 for my specific setup, adjust as needed.
        invert=True,
        spi_speed_hz=40_000_000
    )
    disp.begin()
    return disp


def limpar_display():
    global disp
    img = Image.new("RGB", (LARGURA, ALTURA), (0, 0, 0))
    disp.display(img)


def obter_fase_lua(instante_local=None):
    if instante_local is None:
        instante_local = datetime.now(ZoneInfo(TIMEZONE))

    instante_utc = instante_local.astimezone(ZoneInfo("UTC"))
    data_ephem = ephem.Date(instante_utc)

    lua_nova_anterior = ephem.previous_new_moon(data_ephem)
    idade = float(data_ephem - lua_nova_anterior)

    if idade < 0:
        idade = 0.0
    elif idade > CICLO_LUNAR:
        idade = CICLO_LUNAR

    return idade


def nome_arquivo(fase):
    if fase <= 0:
        num = 1
    else:
        num = round((fase / CICLO_LUNAR) * (TOTAL_IMAGENS - 1)) + 1

    if num < 1:
        num = 1
    elif num > TOTAL_IMAGENS:
        num = TOTAL_IMAGENS

    return f"moon_{num:05d}.png"


def carregar_fonte(tamanho):
    candidatos = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    for caminho in candidatos:
        try:
            return ImageFont.truetype(caminho, tamanho)
        except OSError:
            pass

    return ImageFont.load_default()


def criar_observador(instante_local=None):
    tz_local = ZoneInfo(TIMEZONE)
    tz_utc = ZoneInfo("UTC")

    if instante_local is None:
        instante_local = datetime.now(tz_local)

    instante_utc = instante_local.astimezone(tz_utc)

    obs = ephem.Observer()
    obs.lat = str(LATITUDE)
    obs.lon = str(LONGITUDE)
    obs.date = ephem.Date(instante_utc)

    return obs, instante_local


def obter_fase_e_iluminacao(instante_local=None):
    obs, _ = criar_observador(instante_local)
    lua = ephem.Moon()
    lua.compute(obs)

    iluminacao = None
    if hasattr(lua, "moon_phase"):
        iluminacao = round(float(lua.moon_phase) * 100)
    elif hasattr(lua, "phase"):
        iluminacao = round(float(lua.phase))

    fase_texto = "Desconhecida" # Unknown phase
    fase_num = None

    try:
        agora = obs.date
        lua_nova_anterior = ephem.previous_new_moon(agora)
        lua_nova_proxima = ephem.next_new_moon(agora)
        ciclo_total = float(lua_nova_proxima - lua_nova_anterior)
        idade = float(agora - lua_nova_anterior)

        fase_num = (idade / ciclo_total) * 29.53058867

        if fase_num < 14.765:
            fase_texto = "Crescente" # Crescent - I considered everything from new moon to full moon as "Crescente"
        else:
            fase_texto = "Minguante" # Waning - I considered everything from full moon to new moon as "Minguante"
    except Exception:
        pass

    return fase_texto, iluminacao, fase_num


def obter_posicao_lua(instante_local=None):
    obs, _ = criar_observador(instante_local)
    lua = ephem.Moon()
    lua.compute(obs)

    azimute = round(math.degrees(float(lua.az)))
    elevacao = round(math.degrees(float(lua.alt)))

    return azimute, elevacao


def converter_evento_para_local(evento):
    if evento is None:
        return None

    dt_utc = ephem.Date(evento).datetime().replace(tzinfo=ZoneInfo("UTC"))
    return dt_utc.astimezone(ZoneInfo(TIMEZONE))


def obter_proximos_eventos(instante_local=None):
    obs, _ = criar_observador(instante_local)

    nascer = None
    por = None

    try:
        nascer = obs.next_rising(ephem.Moon())
    except Exception:
        pass

    try:
        por = obs.next_setting(ephem.Moon())
    except Exception:
        pass

    nascer_local = converter_evento_para_local(nascer)
    por_local = converter_evento_para_local(por)

    return nascer_local, por_local


def obter_azimute_evento(instante_local):
    if instante_local is None:
        return None

    obs, _ = criar_observador(instante_local)
    lua = ephem.Moon()
    lua.compute(obs)

    return round(math.degrees(float(lua.az)))


def obter_efeitos_lua(instante_local=None):
    if instante_local is None:
        agora = datetime.now(ZoneInfo(TIMEZONE))
    else:
        agora = instante_local

    obs, _ = criar_observador(agora)
    lua = ephem.Moon()

    nascer_anterior = None
    por_proximo = None

    try:
        nascer_anterior = converter_evento_para_local(obs.previous_rising(lua))
    except Exception:
        pass

    try:
        por_proximo = converter_evento_para_local(obs.next_setting(lua))
    except Exception:
        pass

    try:
        _, elevacao = obter_posicao_lua(agora)
    except Exception:
        elevacao = 0

    intensidade_laranja = 0.0
    intensidade_azul = 0.0
    fator_brilho = 1.0

    if nascer_anterior is not None:
        fim_janela_nascer = nascer_anterior + timedelta(hours=1)
        if nascer_anterior <= agora <= fim_janela_nascer:
            total = 3600
            decorrido = (agora - nascer_anterior).total_seconds()
            intensidade_nascer = max(0.0, min(1.0, 1.0 - (decorrido / total)))
            intensidade_laranja = max(intensidade_laranja, intensidade_nascer)

    if por_proximo is not None:
        inicio_janela_por = por_proximo - timedelta(hours=1)
        if inicio_janela_por <= agora <= por_proximo:
            total = 3600
            decorrido = (agora - inicio_janela_por).total_seconds()
            intensidade_por = max(0.0, min(1.0, decorrido / total))
            intensidade_laranja = max(intensidade_laranja, intensidade_por)

    if elevacao <= 0:
        intensidade_azul = 0.50 # Adjust this value to control the intensity of the blue tint when the moon is below the horizon.
        fator_brilho = 0.50 # Adjust this value to control the brightness factor when the moon is below the horizon.

    return {
        "intensidade_laranja": intensidade_laranja,
        "intensidade_azul": intensidade_azul,
        "fator_brilho": fator_brilho,
        "elevacao": elevacao,
        "nascer": nascer_anterior,
        "por": por_proximo,
    }


def aplicar_efeitos_lua(img, efeitos):
    img = img.convert("RGB")

    brilho = img.convert("L")
    brilho = ImageEnhance.Contrast(brilho).enhance(1.8)

    mascara_claros = brilho.point(
        lambda p: 0 if p < 40 else int(((p - 40) / (255 - 40)) * 255)
    )

    if efeitos["fator_brilho"] != 1.0:
        img = ImageEnhance.Brightness(img).enhance(efeitos["fator_brilho"])

    if efeitos["intensidade_azul"] > 0:
        camada_azul = Image.new("RGB", img.size, "#b4b4ff")
        azul_tingido = Image.blend(img, camada_azul, efeitos["intensidade_azul"])
        img = Image.composite(azul_tingido, img, mascara_claros)

    if efeitos["intensidade_laranja"] > 0:
        camada_laranja = Image.new("RGB", img.size, "#FF560B")
        laranja_tingido = Image.blend(img, camada_laranja, efeitos["intensidade_laranja"] * 0.45)
        img = Image.composite(laranja_tingido, img, mascara_claros)

    return img


def gerar_imagem_lua(instante_local=None):
    fase = obter_fase_lua(instante_local)
    nome = nome_arquivo(fase)
    caminho = ASSETS_DIR / "moon_" / nome

    if not caminho.exists():
        raise FileNotFoundError(f"Imagem não encontrada: {caminho}")

    # ======= This part of the code rotates the moon image based on the current position of the moon and the sun =======
    obs = ephem.Observer()
    obs.lat = str(LATITUDE)
    obs.lon = str(LONGITUDE)
    obs.date = ephem.now()

    moon = ephem.Moon()
    moon.compute(obs)

    sol = ephem.Sun()
    sol.compute(obs)

    H = float(obs.sidereal_time() - moon.ra)
    dec = float(moon.dec)
    lat = float(obs.lat)

    q = math.atan2(
        math.sin(H),
        math.tan(lat) * math.cos(dec) - math.sin(dec) * math.cos(H)
    )

    ra_s, dec_s = float(sol.ra), float(sol.dec)
    ra_m = float(moon.ra)

    chi = math.atan2(
        math.cos(dec_s) * math.sin(ra_s - ra_m),
        math.sin(dec_s) * math.cos(dec) - math.cos(dec_s) * math.sin(dec) * math.cos(ra_s - ra_m)
    )

    angulo = math.degrees(q) - math.degrees(chi) - 90 # If the moon is not correctly oriented, try changing the sign of the angles here.
    #========================================================================================================================

    img = (
        Image.open(caminho)
        .convert("RGB")
        .resize((LARGURA, ALTURA))
        .rotate(- angulo, resample=Image.BICUBIC, expand=False)
        )

    efeitos = obter_efeitos_lua(instante_local)
    img = aplicar_efeitos_lua(img, efeitos)

    return img


def obter_dados_tela2():
    movimento, iluminacao, _ = obter_fase_e_iluminacao()
    azimute, elevacao = obter_posicao_lua()
    dt = datetime.now(ZoneInfo(TIMEZONE))
    nascer, por = obter_proximos_eventos()
    azimute_nascer = obter_azimute_evento(nascer)
    azimute_por = obter_azimute_evento(por)

    return {
        "movimento": movimento,
        "iluminacao": iluminacao if iluminacao is not None else 0,
        "azimute": azimute,
        "elevacao": elevacao,
        "nascer": nascer.strftime("%H:%M") if nascer else "--:--",
        "por": por.strftime("%H:%M") if por else "--:--",
        "azimute_nascer": azimute_nascer,
        "azimute_por": azimute_por,
        "instante_nascer": nascer,
        "instante_por": por,
        "dt": dt.strftime("%d-%b %H:%M"),
    }


def desenhar_texto_centralizado(draw, y, texto, fonte, cor):
    draw.text(
        (LARGURA // 2, y),
        texto,
        font=fonte,
        fill=cor,
        anchor="ma"
    )


def gerar_imagem_info_lua():
    dados = obter_dados_tela2()

        instante = datetime.now(ZoneInfo(TIMEZONE))
    img = gerar_imagem_lua(instante)
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(0.3) # Adjusts the brightness of the background image for better readability of the text.

    draw = ImageDraw.Draw(img)
    
    fonte_titulo = carregar_fonte(20)
    fonte_label = carregar_fonte(14)
    fonte_valor = carregar_fonte(18)
    fonte_evento = carregar_fonte(16)

    cor_titulo = (177, 121, 250)
    cor_label = (100, 100, 255)
    cor_valor = (160, 160, 255)
    cor_evento = (191, 191, 240)
    cor_posicao = (210, 210, 255)
    cor_invisivel = (200, 200, 200)

    desenhar_texto_centralizado(draw, 24, dados["dt"], fonte_titulo, cor_titulo)

    desenhar_texto_centralizado(
        draw,
        62,
        f'{dados["movimento"]}, {dados["iluminacao"]}%',
        fonte_valor,
        cor_valor
    )

    desenhar_texto_centralizado(draw, 92, "Posição atual", fonte_label, cor_label)

    posicao_txt = f'{dados["azimute"]:03d}° Az | {dados["elevacao"]:03d}° El'

    if dados["elevacao"] < 0:
        desenhar_texto_centralizado(draw, 114, posicao_txt, fonte_valor, cor_invisivel)
    else:
        desenhar_texto_centralizado(draw, 114, posicao_txt, fonte_valor, cor_posicao)

    draw.line((28, 145, 212, 145), fill=(55, 55, 55), width=1)

    eventos = []

    if dados["instante_nascer"] is not None:
        eventos.append({
            "tipo": "Nascer",
            "hora": dados["nascer"],
            "azimute": dados["azimute_nascer"],
            "instante": dados["instante_nascer"],
        })

    if dados["instante_por"] is not None:
        eventos.append({
            "tipo": "Pôr",
            "hora": dados["por"],
            "azimute": dados["azimute_por"],
            "instante": dados["instante_por"],
        })

    eventos.sort(key=lambda e: e["instante"])

    linhas = []
    for evento in eventos[:2]:
        if evento["azimute"] is not None:
            linhas.append(f'{evento["tipo"]}: {evento["hora"]} | {evento["azimute"]}°')
        else:
            linhas.append(f'{evento["tipo"]}: {evento["hora"]} | ---°')

    while len(linhas) < 2:
        linhas.append("---")

    desenhar_texto_centralizado(draw, 154, linhas[0], fonte_evento, cor_evento)
    desenhar_texto_centralizado(draw, 186, linhas[1], fonte_evento, cor_evento)

    return img


def atualizar_tela():
    global tela_atual, disp

    if tela_atual == TELA_IMAGEM:
        fase = obter_fase_lua()
        nome = nome_arquivo(fase)
        print(f"Exibindo: {nome} | Idade lunar: {fase:.2f} dias")
        imagem = gerar_imagem_lua()
    else:
        print("Atualizando tela 2...")
        imagem = gerar_imagem_info_lua()

    disp.display(imagem)


def configurar_botao():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BOTAO_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def desligar_raspberry():
    print("Limpando display...")
    limpar_display()
    time.sleep(0.3)

    print("Executando shutdown seguro do Raspberry...")
    rc = subprocess.call(["sudo", "-n", "shutdown", "-h", "now"])

    if rc != 0:
        print("Falha no shutdown. Verifique permissões do sudoers.")


def finalizar(signum=None, frame=None):
    try:
        limpar_display()
    except Exception:
        pass

    try:
        GPIO.cleanup()
    except Exception:
        pass

    sys.exit(0)


def main():
    global disp, tela_atual

    disp = inicializar_display()
    configurar_botao()

    signal.signal(signal.SIGINT, finalizar)
    signal.signal(signal.SIGTERM, finalizar)

    atualizar_tela()

    botao_anterior = GPIO.input(BOTAO_GPIO)
    pressionado_em = None
    ultima_atualizacao_tela_imagem = time.monotonic()
    ultima_atualizacao_tela_info = time.monotonic()

    while True:
        try:
            agora_monotonic = time.monotonic()
            botao_atual = GPIO.input(BOTAO_GPIO)

            if botao_anterior == GPIO.HIGH and botao_atual == GPIO.LOW:
                pressionado_em = agora_monotonic

            elif botao_anterior == GPIO.LOW and botao_atual == GPIO.HIGH:
                if pressionado_em is not None:
                    duracao = agora_monotonic - pressionado_em
                    pressionado_em = None

                    if duracao >= TEMPO_PRESSAO_LONGA:
                        print("Pressão longa detectada. Shutdown solicitado.")
                        desligar_raspberry()
                        time.sleep(2)
                    else:
                        tela_atual = TELA_INFO if tela_atual == TELA_IMAGEM else TELA_IMAGEM
                        print("Toque curto detectado. Alternando tela.")
                        atualizar_tela()

                        if tela_atual == TELA_IMAGEM:
                            ultima_atualizacao_tela_imagem = agora_monotonic
                        else:
                            ultima_atualizacao_tela_info = agora_monotonic

            if tela_atual == TELA_IMAGEM:
                if (agora_monotonic - ultima_atualizacao_tela_imagem) >= INTERVALO_TELA_IMAGEM:
                    atualizar_tela()

                    ultima_atualizacao_tela_imagem = agora_monotonic

            elif tela_atual == TELA_INFO:
                if (agora_monotonic - ultima_atualizacao_tela_info)>= INTERVALO_TELA_INFO:
                    atualizar_tela()

                    ultima_atualizacao_tela_info = agora_monotonic

            botao_anterior = botao_atual
            time.sleep(INTERVALO_LOOP)

        except FileNotFoundError as e:
            print(e)
            time.sleep(1)
        except Exception as e:
            print(f"Erro: {e}")
            time.sleep(1)


if __name__ == "__main__":
    main()

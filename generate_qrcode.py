#!/usr/bin/env python3
"""Gera QR Code para a URL da aplicação."""

try:
    import qrcode
    
    url = 'https://florencia-oligocarpous-bristly.ngrok-free.dev'
    
    # Cria o QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # Gera a imagem
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Salva em arquivo
    img.save('qrcode_app.png')
    print('✓ QR Code gerado com sucesso: qrcode_app.png')
    print(f'✓ URL: {url}')
    
except ImportError:
    print('✗ Erro: biblioteca qrcode não instalada')
    print('  Execute: pip install qrcode[pil]')
    exit(1)
except Exception as e:
    print(f'✗ Erro ao gerar QR Code: {e}')
    exit(1)

# -*- coding: utf-8 -*-
"""
Punto de entrada principal del Cotizador Aroluz
"""
import sys
import io

# Forzar UTF-8 en stdout/stderr para que los emojis en print() no fallen
# en terminales Windows que usan cp1252 por defecto.
if hasattr(sys.stdout, 'buffer') and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

if __name__ == "__main__":
    from gui import main
    main()


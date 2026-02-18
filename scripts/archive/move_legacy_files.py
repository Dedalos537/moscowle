#!/usr/bin/env python3
"""
Script para mover archivos legacy a la carpeta de backup.
Ejecuta este script desde la raíz del proyecto: python move_legacy_files.py
"""

import os
import shutil
from pathlib import Path

# Archivos a mover
LEGACY_FILES = [
    'templates/dashboard.html',
    'templates/calendar_patient.html',
    'templates/my_therapist.html',
    'templates/progress.html',
    'templates/games.html',
    'templates/base.html',
    'templates/manage_patients.html',  # Reemplazado por therapist/patients.html
]

# Archivos que NO deben moverse (importantes)
KEEP_FILES = [
    'templates/game.html',  # Juego de reflejos - USADO
    'templates/login.html',  # Login - USADO
]

def main():
    print("🗂️  Moviendo archivos legacy a carpeta de backup...\n")
    
    backup_dir = Path('templates/_legacy_backup')
    backup_dir.mkdir(exist_ok=True)
    
    moved_count = 0
    skipped_count = 0
    
    for file_path in LEGACY_FILES:
        source = Path(file_path)
        
        if not source.exists():
            print(f"⚠️  {file_path} - No existe, omitiendo")
            skipped_count += 1
            continue
        
        # Nombre del archivo de destino
        destination = backup_dir / source.name
        
        try:
            # Mover archivo
            shutil.move(str(source), str(destination))
            print(f"✅ Movido: {file_path} → {destination}")
            moved_count += 1
        except Exception as e:
            print(f"❌ Error moviendo {file_path}: {e}")
            skipped_count += 1
    
    print(f"\n📊 Resumen:")
    print(f"   ✅ Archivos movidos: {moved_count}")
    print(f"   ⚠️  Archivos omitidos: {skipped_count}")
    
    print("\n📁 Archivos importantes que se mantuvieron:")
    for keep_file in KEEP_FILES:
        if Path(keep_file).exists():
            print(f"   ✓ {keep_file}")
    
    print("\n✨ ¡Limpieza completada!")
    print("💡 Los archivos legacy están en: templates/_legacy_backup/")
    print("💡 Lee el README.md en esa carpeta para más información.")

if __name__ == '__main__':
    main()

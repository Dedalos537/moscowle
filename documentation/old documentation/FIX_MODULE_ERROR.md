# 🆘 SOLUCIÓN - ModuleNotFoundError: openpyxl

**Problema:** `ModuleNotFoundError: No module named 'openpyxl'`  
**Causa:** Faltaban dependencias en requirements.txt  
**Estado:** ✅ SOLUCIONADO

---

## 🔧 PASO 1: En el Servidor cPanel/Hostinger

### Conectar por SSH
```bash
ssh tuusuario@centrujuanpabloii.com
cd /home/centroj/moscowle
```

### Instalar Dependencias Faltantes
```bash
pip install openpyxl python-magic python-magic-bin
# O mejor aún, reinstalar todo:
pip install -r requirements.txt --upgrade
```

### Alternativa: Reinstalar desde cero
```bash
# Borrar directorio virtual anterior
rm -rf venv

# Crear nuevo virtual environment
python3 -m venv venv

# Activar
source venv/bin/activate

# Instalar todo
pip install -r requirements.txt
```

---

## 🔧 PASO 2: Reiniciar la Aplicación

### En cPanel (Passenger)
**Sistema > Reiniciar aplicación Passenger**
O tocar este archivo:
```bash
touch passenger_wsgi.py
```

### Por SSH (si usas gunicorn)
```bash
pkill -f gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 passenger_wsgi:application
```

---

## ✅ Verificación

Accede a: `https://centrujuanpabloii.com/moscowle/login`

Si ves la página de login → ✅ **FUNCIONA**

Si aún hay error → Ver "Troubleshooting" abajo

---

## 📦 Dependencias Agregadas

```
openpyxl>=3.0.0          ← Parser de archivos Excel XLSX
python-magic>=0.4.27     ← Detecta tipo MIME de archivos
python-magic-bin>=0.4.14 ← Binario para Windows/Mac
```

---

## 🔍 Para Verificar Dependencias

```bash
# Ver qué está instalado
pip list | grep -E "openpyxl|python-magic"

# O importar en Python
python3 << 'EOF'
import openpyxl
import magic
print("✅ openpyxl y magic instalados correctamente")
EOF
```

---

## 🆘 Si Sigue Sin Funcionar

### Opción A: Contactar Soporte cPanel
```
Problema: ModuleNotFoundError en app v2.0
Necesito: pip install openpyxl python-magic python-magic-bin
O: Reinstalar Python virtual environment
```

### Opción B: Reinstalar desde ZIP Nuevo
```bash
# Descargar nuevo ZIP (con requirements.txt corregido)
wget deploy_moscowle_v2.zip

# Descomprimir
unzip -o deploy_moscowle_v2.zip

# Reinstalar dependencias
pip install -r requirements.txt --upgrade

# Reiniciar Passenger (touch)
touch passenger_wsgi.py
```

---

## 📋 Checklist de Solución

- [ ] SSH conectado al servidor
- [ ] requirements.txt tiene openpyxl, python-magic, python-magic-bin
- [ ] `pip install -r requirements.txt` ejecutado satisfactoriamente
- [ ] Passenger reiniciado (touch passenger_wsgi.py)
- [ ] URL accesible sin errores de módulo
- [ ] `/admin/yape/dashboard` carga correctamente

---

## 🎯 Próximos Pasos

Una vez funcione:
1. Probar importación Yape: POST /admin/yape/import
2. Probar búsqueda: GET /admin/yape/search
3. Probar adjuntos: POST /admin/yape/{op}/attach-receipt

---

## 📞 Notas

- **ZIP actualizado:** deploy_moscowle_v2.zip (1.2 MB)
- **Última actualización:** 19-Mar-2026 13:30 UTC
- **Status:** ✅ Listo para deploy

¿Necesitas ayuda adicional? 📧

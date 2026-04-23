import os

db_path = "neuroforge.db"

if os.path.exists(db_path):
    os.remove(db_path)
    print(f"✅ Base de datos '{db_path}' eliminada con éxito. Lista para reconstruirse.")
else:
    print(f"⚠️ El archivo '{db_path}' no se encontró.")
    
print("Puedes volver a ejecutar 'streamlit run dashboard.py'.")
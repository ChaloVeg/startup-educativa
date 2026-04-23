from sqlalchemy import inspect
from database import engine

def revisar_esquema():
    inspector = inspect(engine)
    tablas = inspector.get_table_names()
    
    print("\n🔍 ANALIZANDO LA BASE DE DATOS...")
    print("="*50)
    
    if not tablas:
        print("⚠️ La base de datos está completamente vacía (no hay tablas).")
        return
        
    for tabla in tablas:
        print(f"\n📂 TABLA: {tabla}")
        columnas = inspector.get_columns(tabla)
        for col in columnas:
            print(f"   - {col['name']} ({col['type']})")
            
if __name__ == "__main__":
    revisar_esquema()
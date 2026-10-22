import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

# Soporte automático por si se usa el respaldo SQLite local o PostgreSQL de Supabase
try:
    if DATABASE_URL.startswith("sqlite"):
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    else:
        # Normalizar dialecto para psycopg2 si viene como postgresql://
        db_url_pg = DATABASE_URL
        if db_url_pg.startswith("postgresql://"):
            db_url_pg = db_url_pg.replace("postgresql://", "postgresql+psycopg2://", 1)
        temp_engine = create_engine(db_url_pg, connect_args={"connect_timeout": 3}, pool_pre_ping=True)
        with temp_engine.connect() as conn:
            pass
        engine = temp_engine
        print(" [OK] Conectado exitosamente a PostgreSQL (Supabase).")
except Exception as e:
    print(f" [AVISO CONEXION] No se pudo establecer conexión remota con Supabase ({e}).")
    print(" [RESPALDO AUTOMATICO] Iniciando con SQLite local ('sqlite:///./sql_app.db') para garantizar operatividad continua.")
    DATABASE_URL = "sqlite:///./sql_app.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

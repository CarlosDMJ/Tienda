import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DEFAULT_SUPABASE_URL = "postgresql://postgres.bqowwqgsmeorgmgjrbgz:Tecnologias123!@aws-0-us-east-2.pooler.supabase.com:6543/postgres"
DATABASE_URL = os.getenv("DATABASE_URL") or DEFAULT_SUPABASE_URL

# Soporte automático por si se usa el respaldo SQLite local o PostgreSQL de Supabase
try:
    if DATABASE_URL.startswith("sqlite"):
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    else:
        # Normalizar dialecto para psycopg2 si viene como postgresql://
        db_url_pg = DATABASE_URL
        if db_url_pg.startswith("postgresql://"):
            db_url_pg = db_url_pg.replace("postgresql://", "postgresql+psycopg2://", 1)
        temp_engine = create_engine(db_url_pg, connect_args={"connect_timeout": 5}, pool_pre_ping=True)
        with temp_engine.connect() as conn:
            pass
        engine = temp_engine
        print(" [OK] Conectado exitosamente a PostgreSQL (Supabase IPv4 Pooler).")
except Exception as e:
    print(f" [AVISO CONEXION] Fallo inicial ({e}). Usando motor directo.")
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

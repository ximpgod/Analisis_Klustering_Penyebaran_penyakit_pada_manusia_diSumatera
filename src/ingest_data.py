"""
Data Ingestion Script - Penyakit Sumatera Utara
Fungsi: Membaca CSV dan melakukan initial data loading ke PostgreSQL
"""

import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, trim, regexp_replace
from pyspark.sql.types import *
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_spark_session():
    """Membuat Spark Session dengan konfigurasi PostgreSQL"""
    spark = SparkSession.builder \
        .appName("PenyakitSumut-DataIngestion") \
        .config("spark.jars", "/opt/bitnami/spark/jars/postgresql-42.6.0.jar") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark

def clean_kabupaten_name(df):
    """Membersihkan nama kabupaten dari spasi berlebihan"""
    return df.withColumn("kabupaten_kota", 
                        regexp_replace(trim(col("kabupaten_kota")), r"\s+", " "))

def validate_data(df):
    """Validasi data dan hapus baris yang tidak valid"""
    print("=== VALIDASI DATA ===")
    print(f"Total baris awal: {df.count()}")
    
    # Hapus baris yang semua nilai numeriknya 0 atau nama kabupaten kosong
    numeric_cols = [c for c in df.columns if c != 'kabupaten_kota']
    
    # Filter baris yang valid
    df_valid = df.filter(
        (col("kabupaten_kota").isNotNull()) & 
        (col("kabupaten_kota") != "") &
        (col("kabupaten_kota") != "Kota")  # Remove invalid "Kota" row
    )
    
    print(f"Total baris setelah validasi: {df_valid.count()}")
    
    # Show sample data
    print("\n=== SAMPLE DATA ===")
    df_valid.show(5, truncate=False)
    
    return df_valid

def insert_kabupaten_data(df):
    """Insert data kabupaten ke PostgreSQL"""
    try:
        # Database connection
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            database=os.getenv('POSTGRES_DB', 'penyakit_db'),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', 'password123')
        )
        cursor = conn.cursor()
        
        # Get unique kabupaten names
        kabupaten_list = [row['kabupaten_kota'] for row in df.select("kabupaten_kota").distinct().collect()]
        
        # Insert kabupaten data
        for kabupaten in kabupaten_list:
            cursor.execute("""
                INSERT INTO kabupaten (nama_kabupaten) 
                VALUES (%s) 
                ON CONFLICT (nama_kabupaten) DO NOTHING
            """, (kabupaten,))
        
        conn.commit()
        print(f"✅ Berhasil insert {len(kabupaten_list)} kabupaten")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error inserting kabupaten data: {e}")

def save_to_parquet(df, output_path):
    """Simpan data ke format Parquet"""
    try:
        df.coalesce(1).write \
            .mode("overwrite") \
            .option("header", "true") \
            .parquet(output_path)
        
        print(f"✅ Data berhasil disimpan ke: {output_path}")
        
    except Exception as e:
        print(f"❌ Error saving to Parquet: {e}")

def main():
    """Main function untuk data ingestion"""
    print("🚀 MEMULAI DATA INGESTION")
    print("=" * 50)
    
    # Create Spark session
    spark = create_spark_session()
    
    try:
        # Define schema
        schema = StructType([
            StructField("kabupaten_kota", StringType(), True),
            StructField("aids_kasus_baru", IntegerType(), True),
            StructField("aids_kasus_kumulatif", IntegerType(), True),
            StructField("campak_suspek", IntegerType(), True),
            StructField("dbd", IntegerType(), True),
            StructField("diare", IntegerType(), True),
            StructField("hiv_kasus_baru", IntegerType(), True),
            StructField("hiv_kasus_kumulatif", IntegerType(), True),
            StructField("kusta", IntegerType(), True),
            StructField("malaria_suspek", IntegerType(), True),
            StructField("pneumonia_balita", IntegerType(), True),
            StructField("tb_paru", IntegerType(), True),
            StructField("tetanus", IntegerType(), True)
        ])
        
        # Read CSV
        csv_path = "/data/Penyakit_Sumut.csv"
        print(f"📖 Membaca data dari: {csv_path}")
        
        df = spark.read \
            .option("header", "true") \
            .option("inferSchema", "false") \
            .schema(schema) \
            .csv(csv_path)
        
        # Clean and validate data
        df_clean = clean_kabupaten_name(df)
        df_valid = validate_data(df_clean)
        
        # Insert kabupaten data to PostgreSQL
        insert_kabupaten_data(df_valid)
        
        # Save to Parquet
        parquet_path = "/data/parquet/penyakit_clean.parquet"
        save_to_parquet(df_valid, parquet_path)
        
        print("\n✅ DATA INGESTION SELESAI")
        
    except Exception as e:
        print(f"❌ Error dalam data ingestion: {e}")
        sys.exit(1)
        
    finally:
        spark.stop()

if __name__ == "__main__":
    main()

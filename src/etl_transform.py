"""
ETL Transform Script - Penyakit Sumatera Utara
Fungsi: Transformasi data, pivot, dan persiapan untuk clustering
"""

import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, isnan, isnull, sum as spark_sum
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_spark_session():
    """Membuat Spark Session"""
    spark = SparkSession.builder \
        .appName("PenyakitSumut-ETLTransform") \
        .config("spark.jars", "/opt/bitnami/spark/jars/postgresql-42.6.0.jar") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark

def read_clean_data(spark):
    """Membaca data yang sudah dibersihkan"""
    parquet_path = "/data/parquet/penyakit_clean.parquet"
    
    try:
        df = spark.read.parquet(parquet_path)
        print(f"✅ Berhasil membaca data dari: {parquet_path}")
        print(f"📊 Total baris: {df.count()}")
        return df
        
    except Exception as e:
        print(f"❌ Error membaca data: {e}")
        sys.exit(1)

def handle_missing_values(df):
    """Menangani missing values - fill dengan 0"""
    print("\n=== HANDLING MISSING VALUES ===")
    
    # Check for null values
    null_counts = []
    for col_name in df.columns:
        if col_name != 'kabupaten_kota':
            null_count = df.filter(col(col_name).isNull() | isnan(col(col_name))).count()
            null_counts.append((col_name, null_count))
    
    # Print null counts
    for col_name, count in null_counts:
        if count > 0:
            print(f"  {col_name}: {count} null values")
    
    # Fill null values with 0
    numeric_cols = [c for c in df.columns if c != 'kabupaten_kota']
    df_filled = df.fillna(0, subset=numeric_cols)
    
    print("✅ Missing values diisi dengan 0")
    return df_filled

def normalize_data(df):
    """Normalisasi data untuk clustering (opsional)"""
    print("\n=== DATA NORMALIZATION ===")
    
    numeric_cols = [c for c in df.columns if c != 'kabupaten_kota']
    
    # Calculate statistics for each column
    stats = {}
    for col_name in numeric_cols:
        max_val = df.agg({col_name: "max"}).collect()[0][0]
        min_val = df.agg({col_name: "min"}).collect()[0][0]
        stats[col_name] = {'max': max_val, 'min': min_val}
        print(f"  {col_name}: min={min_val}, max={max_val}")
    
    # For this use case, we'll keep original values for better interpretability
    # But you can implement min-max normalization here if needed
    
    return df

def create_feature_summary(df):
    """Membuat summary statistik"""
    print("\n=== FEATURE SUMMARY ===")
    
    numeric_cols = [c for c in df.columns if c != 'kabupaten_kota']
    
    # Calculate totals per kabupaten
    df_with_total = df.withColumn(
        "total_kasus", 
        sum([col(c) for c in numeric_cols])
    )
    
    # Show top kabupaten by total cases
    print("\nTop 10 Kabupaten berdasarkan total kasus:")
    df_with_total.select("kabupaten_kota", "total_kasus") \
        .orderBy(col("total_kasus").desc()) \
        .show(10, truncate=False)
    
    return df

def save_pivot_to_postgres(df):
    """Simpan data pivot ke PostgreSQL"""
    print("\n=== SAVING TO POSTGRESQL ===")
    
    try:
        # PostgreSQL connection properties
        postgres_url = f"jdbc:postgresql://{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
        properties = {
            "user": os.getenv('POSTGRES_USER'),
            "password": os.getenv('POSTGRES_PASSWORD'),
            "driver": "org.postgresql.Driver"
        }
        
        # Save to PostgreSQL
        df.write \
            .mode("overwrite") \
            .jdbc(url=postgres_url, table="data_pivot", properties=properties)
        
        print("✅ Data berhasil disimpan ke PostgreSQL table: data_pivot")
        
    except Exception as e:
        print(f"❌ Error saving to PostgreSQL: {e}")

def save_to_parquet(df, output_path):
    """Simpan data yang sudah ditransformasi ke Parquet"""
    try:
        df.coalesce(1).write \
            .mode("overwrite") \
            .parquet(output_path)
        
        print(f"✅ Data transformed berhasil disimpan ke: {output_path}")
        
    except Exception as e:
        print(f"❌ Error saving to Parquet: {e}")

def main():
    """Main function untuk ETL Transform"""
    print("🔄 MEMULAI ETL TRANSFORMATION")
    print("=" * 50)
    
    # Create Spark session
    spark = create_spark_session()
    
    try:
        # Read clean data
        df = read_clean_data(spark)
        
        # Handle missing values
        df_filled = handle_missing_values(df)
        
        # Normalize data (optional)
        df_normalized = normalize_data(df_filled)
        
        # Create feature summary
        df_final = create_feature_summary(df_normalized)
        
        # Save to PostgreSQL
        save_pivot_to_postgres(df_final)
        
        # Save to Parquet for clustering
        parquet_path = "/data/parquet/penyakit_transformed.parquet"
        save_to_parquet(df_final, parquet_path)
        
        print("\n✅ ETL TRANSFORMATION SELESAI")
        
    except Exception as e:
        print(f"❌ Error dalam ETL transformation: {e}")
        sys.exit(1)
        
    finally:
        spark.stop()

if __name__ == "__main__":
    main()

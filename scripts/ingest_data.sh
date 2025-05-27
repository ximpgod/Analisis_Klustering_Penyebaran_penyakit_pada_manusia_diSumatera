#!/bin/bash

# Script untuk Data Ingestion - Penyakit Sumatera Utara
# Menjalankan proses pembacaan CSV dan data cleaning

set -e  # Exit on any error

echo "🚀 MEMULAI DATA INGESTION"
echo "========================================="

# Check if data file exists
if [ ! -f "/data/Penyakit_Sumut.csv" ]; then
    echo "❌ Error: File /data/Penyakit_Sumut.csv tidak ditemukan!"
    exit 1
fi

# Create necessary directories
mkdir -p /data/parquet
mkdir -p /data/output

echo "📂 Direktori output telah dibuat"

# Download PostgreSQL JDBC driver if not exists
JDBC_JAR="/opt/bitnami/spark/jars/postgresql-42.6.0.jar"
if [ ! -f "$JDBC_JAR" ]; then
    echo "📥 Downloading PostgreSQL JDBC driver..."
    wget -q https://jdbc.postgresql.org/download/postgresql-42.6.0.jar -O $JDBC_JAR
    echo "✅ PostgreSQL JDBC driver downloaded"
fi

# Wait for PostgreSQL to be ready
echo "⏳ Menunggu PostgreSQL siap..."
until pg_isready -h postgres -p 5432 -U postgres; do
    echo "  PostgreSQL belum siap, menunggu 5 detik..."
    sleep 5
done
echo "✅ PostgreSQL sudah siap"

# Install required Python packages
echo "📦 Installing required Python packages..."
pip install -q python-dotenv psycopg2-binary matplotlib seaborn pandas

# Run the ingestion script
echo "🔄 Menjalankan script data ingestion..."
cd /app

python ingest_data.py

if [ $? -eq 0 ]; then
    echo "✅ DATA INGESTION BERHASIL DISELESAIKAN"
    echo "📊 Data telah dibersihkan dan disimpan ke:"
    echo "   - PostgreSQL: table kabupaten"
    echo "   - Parquet: /data/parquet/penyakit_clean.parquet"
else
    echo "❌ DATA INGESTION GAGAL"
    exit 1
fi

echo "========================================="

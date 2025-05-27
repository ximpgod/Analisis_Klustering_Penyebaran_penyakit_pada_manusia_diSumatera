#!/bin/bash

# Script untuk ETL Transform - Penyakit Sumatera Utara
# Menjalankan proses transformasi dan persiapan data untuk clustering

set -e  # Exit on any error

echo "🔄 MEMULAI ETL TRANSFORMATION"
echo "========================================="

# Check if clean data exists
if [ ! -d "/data/parquet/penyakit_clean.parquet" ]; then
    echo "❌ Error: Clean data tidak ditemukan!"
    echo "   Jalankan ingest_data.sh terlebih dahulu"
    exit 1
fi

# Wait for PostgreSQL to be ready
echo "⏳ Menunggu PostgreSQL siap..."
until pg_isready -h postgres -p 5432 -U postgres; do
    echo "  PostgreSQL belum siap, menunggu 5 detik..."
    sleep 5
done
echo "✅ PostgreSQL sudah siap"

# Install required Python packages if not already installed
echo "📦 Checking Python packages..."
pip install -q python-dotenv psycopg2-binary

# Run the ETL transform script
echo "🔄 Menjalankan script ETL transformation..."
cd /app

python etl_transform.py

if [ $? -eq 0 ]; then
    echo "✅ ETL TRANSFORMATION BERHASIL DISELESAIKAN"
    echo "📊 Data telah ditransformasi dan disimpan ke:"
    echo "   - PostgreSQL: table data_pivot"
    echo "   - Parquet: /data/parquet/penyakit_transformed.parquet"
    
    # Verify transformation results
    echo ""
    echo "🔍 Verifikasi hasil transformasi:"
    
    # Count records in PostgreSQL
    RECORD_COUNT=$(psql -h postgres -U postgres -d penyakit_db -t -c "SELECT COUNT(*) FROM data_pivot;" 2>/dev/null || echo "0")
    echo "   Records in data_pivot table: $RECORD_COUNT"
    
    if [ "$RECORD_COUNT" -gt "0" ]; then
        echo "✅ Transformasi berhasil - data tersedia untuk clustering"
    else
        echo "⚠️  Warning: Tidak ada data di table data_pivot"
    fi
    
else
    echo "❌ ETL TRANSFORMATION GAGAL"
    exit 1
fi

echo "========================================="

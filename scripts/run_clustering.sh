#!/bin/bash

# Script untuk Clustering - Penyakit Sumatera Utara
# Menjalankan proses KMeans clustering menggunakan Spark MLlib

set -e  # Exit on any error

echo "🧠 MEMULAI CLUSTERING ANALYSIS"
echo "========================================="

# Check if transformed data exists
if [ ! -d "/data/parquet/penyakit_transformed.parquet" ]; then
    echo "❌ Error: Transformed data tidak ditemukan!"
    echo "   Jalankan etl_transform.sh terlebih dahulu"
    exit 1
fi

# Wait for Spark Master to be ready
echo "⏳ Menunggu Spark Master siap..."
until curl -f http://spark-master:8080 > /dev/null 2>&1; do
    echo "  Spark Master belum siap, menunggu 5 detik..."
    sleep 5
done
echo "✅ Spark Master sudah siap"

# Wait for PostgreSQL to be ready
echo "⏳ Menunggu PostgreSQL siap..."
until pg_isready -h postgres -p 5432 -U postgres; do
    echo "  PostgreSQL belum siap, menunggu 5 detik..."
    sleep 5
done
echo "✅ PostgreSQL sudah siap"

# Install required Python packages
echo "📦 Installing required Python packages..."
pip install -q python-dotenv psycopg2-binary matplotlib seaborn pandas scikit-learn

# Create output directories
mkdir -p /data/output
mkdir -p /data/output/plots

# Run the clustering script
echo "🔄 Menjalankan script clustering..."
cd /app

# Run with Spark Submit for better resource management
spark-submit \
    --master spark://spark-master:7077 \
    --deploy-mode client \
    --driver-memory 1g \
    --executor-memory 1g \
    --executor-cores 1 \
    --total-executor-cores 2 \
    --jars /opt/bitnami/spark/jars/postgresql-42.6.0.jar \
    run_clustering.py

CLUSTERING_EXIT_CODE=$?

if [ $CLUSTERING_EXIT_CODE -eq 0 ]; then
    echo "✅ CLUSTERING ANALYSIS BERHASIL DISELESAIKAN"
    echo "📊 Hasil clustering telah disimpan ke:"
    echo "   - PostgreSQL: table hasil_klaster"
    echo "   - Parquet: /data/parquet/clustering_results.parquet"
    echo "   - CSV: /data/output/clustering_results.csv"
    
    # Verify clustering results
    echo ""
    echo "🔍 Verifikasi hasil clustering:"
    
    # Count records in PostgreSQL
    CLUSTER_COUNT=$(psql -h postgres -U postgres -d penyakit_db -t -c "SELECT COUNT(*) FROM hasil_klaster;" 2>/dev/null || echo "0")
    echo "   Records in hasil_klaster table: $CLUSTER_COUNT"
    
    # Count unique clusters
    UNIQUE_CLUSTERS=$(psql -h postgres -U postgres -d penyakit_db -t -c "SELECT COUNT(DISTINCT cluster_id) FROM hasil_klaster;" 2>/dev/null || echo "0")
    echo "   Number of unique clusters: $UNIQUE_CLUSTERS"
    
    if [ "$CLUSTER_COUNT" -gt "0" ] && [ "$UNIQUE_CLUSTERS" -gt "1" ]; then
        echo "✅ Clustering berhasil - $UNIQUE_CLUSTERS cluster terbentuk untuk $CLUSTER_COUNT kabupaten"
        
        # Show cluster distribution
        echo ""
        echo "📈 Distribusi cluster:"
        psql -h postgres -U postgres -d penyakit_db -c "SELECT cluster_id, COUNT(*) as jumlah_kabupaten FROM hasil_klaster GROUP BY cluster_id ORDER BY cluster_id;" 2>/dev/null || echo "   Error retrieving cluster distribution"
    else
        echo "⚠️  Warning: Hasil clustering tidak sesuai ekspektasi"
    fi
    
else
    echo "❌ CLUSTERING ANALYSIS GAGAL"
    exit 1
fi

echo "========================================="

#!/bin/bash

# Script untuk Export Results - Penyakit Sumatera Utara
# Menjalankan proses export hasil clustering untuk visualisasi

set -e  # Exit on any error

echo "📤 MEMULAI EXPORT RESULTS"
echo "========================================="

# Check if clustering results exist in PostgreSQL
echo "🔍 Checking clustering results..."
CLUSTER_COUNT=$(psql -h postgres -U postgres -d penyakit_db -t -c "SELECT COUNT(*) FROM hasil_klaster;" 2>/dev/null || echo "0")

if [ "$CLUSTER_COUNT" -eq "0" ]; then
    echo "❌ Error: Hasil clustering tidak ditemukan di PostgreSQL!"
    echo "   Jalankan run_clustering.sh terlebih dahulu"
    exit 1
fi

echo "✅ Ditemukan $CLUSTER_COUNT records clustering results"

# Wait for PostgreSQL to be ready
echo "⏳ Menunggu PostgreSQL siap..."
until pg_isready -h postgres -p 5432 -U postgres; do
    echo "  PostgreSQL belum siap, menunggu 5 detik..."
    sleep 5
done
echo "✅ PostgreSQL sudah siap"

# Install required Python packages
echo "📦 Installing required Python packages..."
pip install -q python-dotenv psycopg2-binary matplotlib seaborn pandas openpyxl

# Create output directories
mkdir -p /data/output
mkdir -p /data/output/plots
mkdir -p /data/output/tableau

# Run the export results script
echo "🔄 Menjalankan script export results..."
cd /app

python export_results.py

EXPORT_EXIT_CODE=$?

if [ $EXPORT_EXIT_CODE -eq 0 ]; then
    echo "✅ EXPORT RESULTS BERHASIL DISELESAIKAN"
    echo ""
    echo "📁 File yang telah dibuat:"
    
    # List generated files
    echo "📊 Data Files:"
    ls -la /data/output/*.csv 2>/dev/null || echo "   No CSV files found"
    ls -la /data/output/*.txt 2>/dev/null || echo "   No TXT files found"
    
    echo ""
    echo "📈 Visualization Files:"
    ls -la /data/output/plots/ 2>/dev/null || echo "   No plot files found"
    
    # Create additional exports for different tools
    echo ""
    echo "🔄 Creating additional exports..."
    
    # Export untuk Tableau (format yang lebih clean)
    echo "📊 Creating Tableau-ready export..."
    psql -h postgres -U postgres -d penyakit_db -c "\COPY (
        SELECT 
            hk.kabupaten,
            hk.cluster_id,
            dp.aids_kasus_baru,
            dp.aids_kasus_kumulatif,
            dp.campak_suspek,
            dp.dbd,
            dp.diare,
            dp.hiv_kasus_baru,
            dp.hiv_kasus_kumulatif,
            dp.kusta,
            dp.malaria_suspek,
            dp.pneumonia_balita,
            dp.tb_paru,
            dp.tetanus,
            (dp.aids_kasus_baru + dp.dbd + dp.diare + dp.tb_paru) as total_major_diseases
        FROM hasil_klaster hk
        JOIN data_pivot dp ON hk.kabupaten = dp.kabupaten
        ORDER BY hk.cluster_id, hk.kabupaten
    ) TO '/data/output/tableau_export.csv' WITH CSV HEADER;" 2>/dev/null
    
    # Export summary statistics
    echo "📈 Creating summary statistics..."
    psql -h postgres -U postgres -d penyakit_db -c "\COPY (
        SELECT 
            cluster_id,
            COUNT(*) as jumlah_kabupaten,
            AVG(aids_kasus_baru) as avg_aids,
            AVG(dbd) as avg_dbd,
            AVG(diare) as avg_diare,
            AVG(tb_paru) as avg_tb_paru,
            SUM(aids_kasus_baru + dbd + diare + tb_paru) as total_major_diseases_per_cluster
        FROM hasil_klaster hk
        JOIN data_pivot dp ON hk.kabupaten = dp.kabupaten
        GROUP BY cluster_id
        ORDER BY cluster_id
    ) TO '/data/output/cluster_summary_stats.csv' WITH CSV HEADER;" 2>/dev/null
    
    echo "✅ Additional exports created"
    
    # Verify all exports
    echo ""
    echo "🔍 Verifikasi final exports:"
    
    EXPECTED_FILES=(
        "/data/output/clustering_results_detailed.csv"
        "/data/output/cluster_statistics.csv"
        "/data/output/clustering_summary_report.txt"
        "/data/output/tableau_export.csv"
        "/data/output/cluster_summary_stats.csv"
    )
    
    for file in "${EXPECTED_FILES[@]}"; do
        if [ -f "$file" ]; then
            SIZE=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "unknown")
            echo "✅ $file ($SIZE bytes)"
        else
            echo "❌ $file - NOT FOUND"
        fi
    done
    
    echo ""
    echo "🎯 SIAP UNTUK VISUALISASI:"
    echo "   📊 Tableau: gunakan /data/output/tableau_export.csv"
    echo "   📓 Jupyter: gunakan /data/output/clustering_results_detailed.csv"
    echo "   📈 Analysis: baca /data/output/clustering_summary_report.txt"
    
else
    echo "❌ EXPORT RESULTS GAGAL"
    exit 1
fi

echo "========================================="

#!/bin/bash

# Master Pipeline Script - Penyakit Sumatera Utara
# Menjalankan seluruh pipeline end-to-end clustering

set -e  # Exit on any error

echo "🚀 MEMULAI COMPLETE PIPELINE - CLUSTERING PENYAKIT SUMATERA UTARA"
echo "======================================================================="
echo "📅 Started at: $(date)"
echo ""

print_status() {
    echo ""
    echo "🔄 $1"
    echo "----------------------------------------"
}

# Function to check service health
check_service() {
    local service_name=$1
    local health_command=$2
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if eval $health_command > /dev/null 2>&1; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        
        echo "  Attempt $attempt/$max_attempts - $service_name not ready, waiting 10 seconds..."
        sleep 10
        attempt=$((attempt + 1))
    done
    
    echo "❌ $service_name failed to start after $max_attempts attempts"
    return 1
}

# Check prerequisites
print_status "CHECKING PREREQUISITES"

if [ ! -f "/data/Penyakit_Sumut.csv" ]; then
    echo "❌ Error: Source data file not found!"
    echo "   Expected: /data/Penyakit_Sumut.csv"
    exit 1
fi

echo "✅ Source data file found"

# Wait for all services to be ready
print_status "WAITING FOR SERVICES"

# Check PostgreSQL
check_service "PostgreSQL" "pg_isready -h postgres -p 5432 -U postgres"

# Check Spark Master
check_service "Spark Master" "curl -f http://spark-master:8080"

# Create necessary directories
print_status "SETTING UP DIRECTORIES"
mkdir -p /data/parquet
mkdir -p /data/output
mkdir -p /data/output/plots
mkdir -p /data/logs

echo "✅ All directories created"

# Stage 1: Data Ingestion
print_status "STAGE 1: DATA INGESTION"
START_TIME=$(date +%s)

bash /scripts/ingest_data.sh

if [ $? -eq 0 ]; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    echo "✅ Stage 1 completed in $DURATION seconds"
else
    echo "❌ Stage 1 failed - Data Ingestion"
    exit 1
fi

# Stage 2: ETL Transform
print_status "STAGE 2: ETL TRANSFORMATION"
START_TIME=$(date +%s)

bash /scripts/etl_transform.sh

if [ $? -eq 0 ]; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    echo "✅ Stage 2 completed in $DURATION seconds"
else
    echo "❌ Stage 2 failed - ETL Transformation"
    exit 1
fi

# Stage 3: Clustering
print_status "STAGE 3: CLUSTERING ANALYSIS"
START_TIME=$(date +%s)

bash /scripts/run_clustering.sh

if [ $? -eq 0 ]; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    echo "✅ Stage 3 completed in $DURATION seconds"
else
    echo "❌ Stage 3 failed - Clustering Analysis"
    exit 1
fi

# Stage 4: Export Results
print_status "STAGE 4: EXPORT RESULTS"
START_TIME=$(date +%s)

bash /scripts/export_results.sh

if [ $? -eq 0 ]; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    echo "✅ Stage 4 completed in $DURATION seconds"
else
    echo "❌ Stage 4 failed - Export Results"
    exit 1
fi

# Final verification
print_status "FINAL VERIFICATION"

echo "🔍 Verifying pipeline outputs..."

# Check PostgreSQL tables
TABLES=("kabupaten" "penyakit" "kasus_penyakit" "hasil_klaster" "data_pivot")
for table in "${TABLES[@]}"; do
    COUNT=$(psql -h postgres -U postgres -d penyakit_db -t -c "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "0")
    if [ "$COUNT" -gt "0" ]; then
        echo "✅ Table $table: $COUNT records"
    else
        echo "⚠️  Table $table: No data"
    fi
done

# Check output files
OUTPUT_FILES=(
    "/data/parquet/penyakit_clean.parquet"
    "/data/parquet/penyakit_transformed.parquet"
    "/data/parquet/clustering_results.parquet"
    "/data/output/tableau_export.csv"
    "/data/output/cluster_summary_stats.csv"
    "/data/output/clustering_summary_report.txt"
)

echo ""
echo "📁 Output files verification:"
for file in "${OUTPUT_FILES[@]}"; do
    if [ -f "$file" ] || [ -d "$file" ]; then
        if [ -f "$file" ]; then
            SIZE=$(stat -c%s "$file" 2>/dev/null || echo "unknown")
            echo "✅ $file ($SIZE bytes)"
        else
            echo "✅ $file (directory)"
        fi
    else
        echo "❌ $file (missing)"
    fi
done

# Summary
print_status "PIPELINE SUMMARY"

echo "🎉 PIPELINE COMPLETED SUCCESSFULLY!"
echo ""
echo "📊 SUMMARY:"
echo "   • Total Kabupaten processed: $(psql -h postgres -U postgres -d penyakit_db -t -c "SELECT COUNT(*) FROM hasil_klaster;" 2>/dev/null || echo "N/A")"
echo "   • Clusters generated: $(psql -h postgres -U postgres -d penyakit_db -t -c "SELECT COUNT(DISTINCT cluster_id) FROM hasil_klaster;" 2>/dev/null || echo "N/A")"
echo "   • Completed at: $(date)"
echo ""
echo "🎯 NEXT STEPS:"
echo "   1. 📓 Open Jupyter Notebook: http://localhost:8888 (token: penyakit123)"
echo "   2. 📊 Import tableau_export.csv to Tableau for visualization"
echo "   3. 🗄️  Access PostgreSQL via pgAdmin: http://localhost:5050"
echo "   4. 📈 Check Spark UI: http://localhost:8080"
echo ""
echo "📂 KEY OUTPUT FILES:"
echo "   • /data/output/tableau_export.csv - For Tableau visualization"
echo "   • /data/output/clustering_summary_report.txt - Complete analysis report"
echo "   • /data/output/cluster_summary_stats.csv - Statistical summary"
echo ""
echo "🔐 ACCESS CREDENTIALS:"
echo "   • Jupyter Token: penyakit123"
echo "   • pgAdmin: admin@admin.com / admin123"
echo "   • PostgreSQL: postgres / password123"

echo "======================================================================="

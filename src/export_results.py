"""
Export Results Script - Penyakit Sumatera Utara
Fungsi: Export hasil clustering untuk visualisasi dan reporting
"""

import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as spark_sum, avg, max as spark_max
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_spark_session():
    """Membuat Spark Session"""
    spark = SparkSession.builder \
        .appName("PenyakitSumut-ExportResults") \
        .config("spark.jars", "/opt/bitnami/spark/jars/postgresql-42.6.0.jar") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark

def read_clustering_results(spark):
    """Membaca hasil clustering"""
    try:
        # Read from PostgreSQL
        postgres_url = f"jdbc:postgresql://{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
        properties = {
            "user": os.getenv('POSTGRES_USER'),
            "password": os.getenv('POSTGRES_PASSWORD'),
            "driver": "org.postgresql.Driver"
        }
        
        # Read clustering results
        df_clusters = spark.read.jdbc(
            url=postgres_url,
            table="hasil_klaster",
            properties=properties
        )
        
        # Read original data with features
        df_data = spark.read.jdbc(
            url=postgres_url,
            table="data_pivot",
            properties=properties
        )
        
        print("✅ Berhasil membaca hasil clustering dari PostgreSQL")
        return df_clusters, df_data
        
    except Exception as e:
        print(f"❌ Error membaca data: {e}")
        sys.exit(1)

def create_cluster_summary(df_clusters, df_data):
    """Membuat summary per cluster"""
    print("\n=== CREATING CLUSTER SUMMARY ===")
    
    # Join clustering results with data
    df_joined = df_clusters.join(
        df_data,
        df_clusters.kabupaten == df_data.kabupaten,
        "inner"
    ).drop(df_data.kabupaten)
    
    # Calculate statistics per cluster
    cluster_stats = df_joined.groupBy("cluster_id").agg(
        spark_sum("dbd").alias("total_dbd"),
        spark_sum("diare").alias("total_diare"),
        spark_sum("tb_paru").alias("total_tb_paru"),
        spark_sum("aids_kasus_baru").alias("total_aids"),
        avg("dbd").alias("avg_dbd"),
        avg("diare").alias("avg_diare"),
        avg("tb_paru").alias("avg_tb_paru"),
        spark_max("dbd").alias("max_dbd")
    ).orderBy("cluster_id")
    
    print("📊 Statistik per cluster:")
    cluster_stats.show(truncate=False)
    
    return df_joined, cluster_stats

def export_to_csv(df_joined, cluster_stats):
    """Export data ke CSV untuk Tableau"""
    print("\n=== EXPORTING TO CSV ===")
    
    try:
        # Create output directory
        os.makedirs("/data/output", exist_ok=True)
        
        # Convert to Pandas and export
        df_pandas = df_joined.toPandas()
        stats_pandas = cluster_stats.toPandas()
        
        # Export main data
        main_csv = "/data/output/clustering_results_detailed.csv"
        df_pandas.to_csv(main_csv, index=False)
        print(f"✅ Main data exported: {main_csv}")
        
        # Export cluster statistics
        stats_csv = "/data/output/cluster_statistics.csv"
        stats_pandas.to_csv(stats_csv, index=False)
        print(f"✅ Cluster statistics exported: {stats_csv}")
        
        # Create summary report
        create_summary_report(df_pandas, stats_pandas)
        
        return df_pandas, stats_pandas
        
    except Exception as e:
        print(f"❌ Error exporting CSV: {e}")

def create_summary_report(df_pandas, stats_pandas):
    """Membuat laporan summary dalam format text"""
    print("\n=== CREATING SUMMARY REPORT ===")
    
    try:
        report_path = "/data/output/clustering_summary_report.txt"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("LAPORAN HASIL CLUSTERING PENYAKIT SUMATERA UTARA\n")
            f.write("=" * 60 + "\n\n")
            
            # General statistics
            f.write("STATISTIK UMUM:\n")
            f.write(f"Total Kabupaten/Kota: {len(df_pandas)}\n")
            f.write(f"Jumlah Cluster: {df_pandas['cluster_id'].nunique()}\n\n")
            
            # Cluster distribution
            f.write("DISTRIBUSI CLUSTER:\n")
            cluster_dist = df_pandas['cluster_id'].value_counts().sort_index()
            for cluster_id, count in cluster_dist.items():
                f.write(f"Cluster {cluster_id}: {count} kabupaten/kota\n")
            f.write("\n")
            
            # Top cases by disease
            f.write("TOP 5 KABUPATEN BERDASARKAN PENYAKIT:\n")
            f.write("-" * 40 + "\n")
            
            diseases = ['dbd', 'diare', 'tb_paru', 'aids_kasus_baru']
            for disease in diseases:
                f.write(f"\n{disease.upper()}:\n")
                top_5 = df_pandas.nlargest(5, disease)[['kabupaten', disease, 'cluster_id']]
                for _, row in top_5.iterrows():
                    f.write(f"  {row['kabupaten']}: {row[disease]} (Cluster {row['cluster_id']})\n")
            
            # Cluster characteristics
            f.write("\n\nKARAKTERISTIK CLUSTER:\n")
            f.write("-" * 40 + "\n")
            
            for cluster_id in sorted(df_pandas['cluster_id'].unique()):
                cluster_data = df_pandas[df_pandas['cluster_id'] == cluster_id]
                f.write(f"\nCLUSTER {cluster_id}:\n")
                f.write(f"  Jumlah wilayah: {len(cluster_data)}\n")
                f.write(f"  Wilayah: {', '.join(cluster_data['kabupaten'].tolist())}\n")
                f.write(f"  Rata-rata DBD: {cluster_data['dbd'].mean():.1f}\n")
                f.write(f"  Rata-rata Diare: {cluster_data['diare'].mean():.1f}\n")
                f.write(f"  Rata-rata TB Paru: {cluster_data['tb_paru'].mean():.1f}\n")
        
        print(f"✅ Summary report saved: {report_path}")
        
    except Exception as e:
        print(f"❌ Error creating summary report: {e}")

def create_visualizations(df_pandas):
    """Membuat visualisasi basic (untuk reference)"""
    print("\n=== CREATING BASIC VISUALIZATIONS ===")
    
    try:
        # Set style
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Create output directory for plots
        os.makedirs("/data/output/plots", exist_ok=True)
        
        # 1. Cluster distribution
        plt.figure(figsize=(10, 6))
        cluster_counts = df_pandas['cluster_id'].value_counts().sort_index()
        plt.bar(cluster_counts.index, cluster_counts.values)
        plt.title('Distribusi Jumlah Kabupaten per Cluster')
        plt.xlabel('Cluster ID')
        plt.ylabel('Jumlah Kabupaten')
        plt.grid(True, alpha=0.3)
        plt.savefig('/data/output/plots/cluster_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Disease comparison by cluster
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        diseases = ['dbd', 'diare', 'tb_paru', 'aids_kasus_baru']
        
        for i, disease in enumerate(diseases):
            ax = axes[i//2, i%2]
            df_pandas.boxplot(column=disease, by='cluster_id', ax=ax)
            ax.set_title(f'Distribusi {disease.upper()} per Cluster')
            ax.set_xlabel('Cluster ID')
            ax.set_ylabel(f'Jumlah Kasus {disease.upper()}')
        
        plt.tight_layout()
        plt.savefig('/data/output/plots/disease_by_cluster.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print("✅ Basic visualizations created in /data/output/plots/")
        
    except Exception as e:
        print(f"❌ Error creating visualizations: {e}")

def validate_exports():
    """Validasi file yang telah diexport"""
    print("\n=== VALIDATING EXPORTS ===")
    
    expected_files = [
        "/data/output/clustering_results_detailed.csv",
        "/data/output/cluster_statistics.csv",
        "/data/output/clustering_summary_report.txt"
    ]
    
    for file_path in expected_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✅ {file_path} - {size} bytes")
        else:
            print(f"❌ {file_path} - NOT FOUND")

def main():
    """Main function untuk export results"""
    print("📤 MEMULAI EXPORT RESULTS")
    print("=" * 50)
    
    # Create Spark session
    spark = create_spark_session()
    
    try:
        # Read clustering results
        df_clusters, df_data = read_clustering_results(spark)
        
        # Create cluster summary
        df_joined, cluster_stats = create_cluster_summary(df_clusters, df_data)
        
        # Export to CSV
        df_pandas, stats_pandas = export_to_csv(df_joined, cluster_stats)
        
        # Create visualizations
        if df_pandas is not None:
            create_visualizations(df_pandas)
        
        # Validate exports
        validate_exports()
        
        print("\n✅ EXPORT RESULTS SELESAI")
        print("\n📋 FILES GENERATED:")
        print("  - /data/output/clustering_results_detailed.csv (untuk Tableau)")
        print("  - /data/output/cluster_statistics.csv")
        print("  - /data/output/clustering_summary_report.txt")
        print("  - /data/output/plots/ (visualisasi basic)")
        
    except Exception as e:
        print(f"❌ Error dalam export results: {e}")
        sys.exit(1)
        
    finally:
        spark.stop()

if __name__ == "__main__":
    main()

# Copilot Instructions for Data Engineering Project: Penyakit Sumut

These instructions guide GitHub Copilot to assist in building and maintaining a big data pipeline for clustering disease cases in North Sumatra. Follow these best practices and coding conventions to ensure clarity and reproducibility.

---

## 🎯 Project Goal

Build a batch processing pipeline that:

* Ingests CSV data of disease cases.
* Transforms and cleans the data.
* Performs clustering with Spark MLlib (KMeans).
* Loads results into a PostgreSQL data warehouse.
* Provides output for visualization in Jupyter and Tableau.

---

## 🛠️ File Structure

```
project_root/
├── data/
│   └── Penyakit_Sumut.csv
├── scripts/
│   ├── ingest_data.sh
│   ├── etl_transform.sh
│   ├── run_clustering.sh
│   └── export_results.sh
├── notebooks/
│   └── exploratory_analysis.ipynb
├── sql/
│   └── schema_postgres.sql
├── README.md
└── copilotinstructions.md
```

---

## ⚙️ Conventions and Standards

* Use **Apache Spark** (PySpark) for ETL and ML tasks.
* Store intermediate data using Parquet format.
* Store final results in **PostgreSQL** with proper schema design.
* Use `.sh` scripts to run all processes end-to-end.
* Modularize Spark logic into Python scripts callable by `.sh`.
* All dataframes must use meaningful column names and avoid nulls.
* Use consistent logging and error handling.

---

## 📂 Database Schema (PostgreSQL)

```sql
CREATE TABLE kabupaten (
  id_kabupaten SERIAL PRIMARY KEY,
  nama_kabupaten VARCHAR(100)
);

CREATE TABLE penyakit (
  id_penyakit SERIAL PRIMARY KEY,
  nama_penyakit VARCHAR(100)
);

CREATE TABLE kasus_penyakit (
  id_kasus SERIAL PRIMARY KEY,
  id_kabupaten INTEGER REFERENCES kabupaten(id_kabupaten),
  id_penyakit INTEGER REFERENCES penyakit(id_penyakit),
  jumlah_kasus INTEGER,
  tahun INTEGER
);

CREATE TABLE hasil_klaster (
  id SERIAL PRIMARY KEY,
  kabupaten VARCHAR(100),
  cluster_id INTEGER
);
```

---

## 🧠 ETL Steps Breakdown

### 1. `ingest_data.sh`

* Load CSV into Spark DataFrame.
* Drop invalid/missing rows.
* Write cleaned data to Parquet.

### 2. `etl_transform.sh`

* Read Parquet data.
* Pivot by `Kabupaten_Kota` vs `Jenis_Penyakit`.
* Fill missing values with zero.

### 3. `run_clustering.sh`

* Assemble features using `VectorAssembler`.
* Train KMeans model (k=4).
* Save results with `kabupaten` and `cluster_id`.

### 4. `export_results.sh`

* Save `cluster_id` and `kabupaten` to PostgreSQL.
* Use JDBC format with proper credentials.

---

## 🧪 Testing Strategy

* Use PySpark’s `.show()` and `.printSchema()` for checks.
* Add assertions for record counts and null checks.
* Visualize output clustering using seaborn or matplotlib in notebooks.

---

## 📊 Visualization Guidance

* Use **Jupyter Notebook** for exploratory clustering summary.
* Use **Tableau** to build:

  * Choropleth maps of cluster regions.
  * Bar plots for disease burden.
  * Time series of disease trends (if applicable).

---

## 🔐 Credentials & Security

* Store PostgreSQL credentials in environment variables.
* Never hardcode passwords in `.py` or `.sh` files.
* Use `.env` + `dotenv` in Python if necessary.

---

## ✅ Copilot Prompts Examples

* "Write PySpark code to read CSV and clean nulls."
* "Pivot dataframe by penyakit and kabupaten."
* "Run KMeans clustering on Spark DataFrame."
* "Write Spark DataFrame to PostgreSQL using JDBC."

---

## 📘 References

* [PySpark Documentation](https://spark.apache.org/docs/latest/api/python/)
* [PostgreSQL Docs](https://www.postgresql.org/docs/)
* [Tableau Public](https://public.tableau.com/)
* [JDBC Spark Guide](https://spark.apache.org/docs/latest/sql-data-sources-jdbc.html)

---

> Maintain modularity, use type-safe Spark APIs, and keep the pipeline reproducible.

---

**Author**: Tim Data Engineering - Institut Teknologi Sumatera

**Last Updated**: Mei 2025

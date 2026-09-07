# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# CELL ********************

# P27 PalmDesk - vendor market feed -> open-mirroring landing zone (Session 1, 2026-09-06)
# Writes three tables into OMD_PalmDesk_Market's landing zone with inserts, updates and deletes:
#   curve       file 1 = initial load (curve dates <= 2026-05-14, version 1)     __rowMarker__ 0
#               file 2 = incremental inserts (curve dates >= 2026-05-15, v1)      __rowMarker__ 0
#               file 3 = 8 UPDATE rows (restated 2026-05-15 CPO curve, v2)        __rowMarker__ 1
#                        + 1 DELETE row (withdrawn PKO quote, 2026-04-24 m7)       __rowMarker__ 2
#   fx_rate     one insert file
#   counterparty one insert file (vendor master)
# Source = WH_PalmDesk (Spark connector for Fabric Warehouse). Landing-zone protocol per Learn
# "Open mirroring landing zone requirements and format": _metadata.json first, then 20-digit sequential parquet.
WORKSPACE_ID = "b06ab341-0860-4341-a6c9-5986d0d7f4b0"
MIRROR_ID = "4b50ee95-6454-4e57-915b-e7cb491d7041"
LZ = f"abfss://{WORKSPACE_ID}@<ONELAKE-HOST>/{MIRROR_ID}/Files/LandingZone"
STAGE = f"abfss://{WORKSPACE_ID}@<ONELAKE-HOST>/{MIRROR_ID}/Files/_nb_stage"
WH = "WH_PalmDesk"
import json
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def read_wh(table):
    return spark.read.synapsesql(f"{WH}.{table}")

curve = read_wh("mkt.curve")
fx = read_wh("mkt.fx_rate")
cp = read_wh("ref.counterparty")
print("warehouse rows:", curve.count(), fx.count(), cp.count())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def ensure_metadata(table, key_columns):
    folder = f"{LZ}/{table}"
    notebookutils.fs.mkdirs(folder)
    notebookutils.fs.put(f"{folder}/_metadata.json", json.dumps({"keyColumns": key_columns}), True)

def next_seq(table):
    folder = f"{LZ}/{table}"
    n = 0
    for sub in ("", "/_ProcessedFiles", "/_FilesReadyToDelete"):
        try:
            for f in notebookutils.fs.ls(folder + sub):
                if f.name.endswith(".parquet"):
                    n += 1
        except Exception:
            pass
    return n + 1

def land(table, df, marker):
    """Write df as the next sequential parquet file in the table's landing folder, with __rowMarker__ = marker."""
    seq = next_seq(table)
    fname = f"{seq:020d}.parquet"
    out = df.withColumn("__rowMarker__", F.lit(marker).cast(IntegerType()))
    tmp = f"{STAGE}/{table}_{seq}"
    out.coalesce(1).write.mode("overwrite").parquet(tmp)
    part = [f.path for f in notebookutils.fs.ls(tmp) if f.name.endswith(".parquet")][0]
    notebookutils.fs.mv(part, f"{LZ}/{table}/{fname}", True)
    notebookutils.fs.rm(tmp, True)
    print(f"landed {table}/{fname}: {out.count()} rows, marker {marker}")
    return fname

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# 1. curve: initial load, incremental inserts, then updates + delete
ensure_metadata("curve", ["curve_date", "product_code", "tenor_month"])
c1 = curve.filter((F.col("version") == 1) & (F.col("curve_date") <= F.lit("2026-05-14")))
c2 = curve.filter((F.col("version") == 1) & (F.col("curve_date") >= F.lit("2026-05-15")))
c3u = curve.filter(F.col("version") == 2)   # restated 2026-05-15 CPO curve: same keys, new price/published_at/version
land("curve", c1, 0)
land("curve", c2, 0)
land("curve", c3u, 1)
# delete: the withdrawn quote (PKO, 2026-04-24, tenor 2026-11) - key columns only, other columns null
c3d = curve.filter((F.col("product_code") == "PKO") & (F.col("curve_date") == F.lit("2026-04-24")) & (F.col("tenor_month") == "2026-11"))
land("curve", c3d, 2)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# 2. fx_rate and counterparty master: inserts
ensure_metadata("fx_rate", ["rate_date", "ccy_pair"])
land("fx_rate", fx, 0)
ensure_metadata("counterparty", ["cp_id"])
land("counterparty", cp, 0)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# 3. evidence: what the landing zone holds now
for t in ("curve", "fx_rate", "counterparty"):
    print(t, [f.name for f in notebookutils.fs.ls(f"{LZ}/{t}")])
print("expected after replication: curve = 2880 - 1 = 2879 rows (8 of them restated), fx_rate = 240, counterparty = 40")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

"""
Membaca wedding_crm_dummy.xlsx dan memasukkan datanya ke database SQLite lokal (wedding_crm.db).
Jalankan ulang file ini setiap kali kamu update data dummy di Excel, untuk sync ke database.

Cara pakai:
    python load_to_sqlite.py
"""
import sqlite3
import pandas as pd

USER = "myuser"
DB_TOKEN = "abcdef"
SOME_KEY = "1234"

EXCEL_FILE = "wedding_crm_dummy.xlsx"
DB_FILE = "wedding_crm.db"

SHEETS = ["Account", "Profile", "Family_Link", "Event", "Revenue", "Notification"]

def main():
    conn = sqlite3.connect(DB_FILE)
    for sheet in SHEETS:
        df = pd.read_excel(EXCEL_FILE, sheet_name=sheet)
        # buang baris catatan (footnote) di bagian bawah sheet: baris data asli
        # selalu punya minimal 2 kolom pertama terisi, baris catatan cuma 1 kolom
        df = df.dropna(subset=df.columns[:2].tolist(), how="any")
        table_name = sheet.lower()
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f"-> tabel '{table_name}': {len(df)} baris dimuat")
    conn.close()
    print(f"\nSelesai. Database tersimpan di {DB_FILE}")

if __name__ == "__main__":
    main()

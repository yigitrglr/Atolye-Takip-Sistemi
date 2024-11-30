from flask import Flask, redirect, render_template, request, flash, url_for, session, jsonify
from datetime import datetime, timedelta
import pandas as pd
import os
import secrets

# Flask app configuration
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # More secure method for production

DETAYLI_KAYIT_DOSYASI = "kayitlar.xlsx"

# Create the Excel file if it doesn't exist
def excel_dosyasi_olustur():
    if not os.path.exists(DETAYLI_KAYIT_DOSYASI):
        detayli_kayit_df = pd.DataFrame(columns=["İsim", "Giriş Zamanı", "Çıkış Zamanı", "Süre"])
        detayli_kayit_df.to_excel(DETAYLI_KAYIT_DOSYASI, index=False, engine='openpyxl')

# Ensure the Excel file exists at startup
excel_dosyasi_olustur()

# Function to write records to the Excel file
def kayitlari_excele_yaz(df):
    try:
        df.to_excel(DETAYLI_KAYIT_DOSYASI, index=False, engine='openpyxl')
    except Exception as e:
        print(f"Veri kaydedilirken bir hata oluştu: {e}")
        flash("Veri kaydedilirken bir hata oluştu. Lütfen tekrar deneyin.")

# Function to read records from the Excel file
def detayli_kayitlari_oku():
    try:
        # Read the Excel file and ensure that only necessary columns are read
        df = pd.read_excel(DETAYLI_KAYIT_DOSYASI, engine='openpyxl', usecols=["İsim", "Giriş Zamanı", "Çıkış Zamanı", "Süre"])
        df.columns = df.columns.str.strip()  # Clean up column names to avoid extra spaces

        # Convert columns to datetime if applicable and ensure proper formatting
        if 'Giriş Zamanı' in df.columns and not df['Giriş Zamanı'].isnull().all():
            df['Giriş Zamanı'] = pd.to_datetime(df['Giriş Zamanı'], errors='coerce').dt.strftime("%Y-%m-%d %H:%M:%S")
        if 'Çıkış Zamanı' in df.columns and not df['Çıkış Zamanı'].isnull().all():
            df['Çıkış Zamanı'] = pd.to_datetime(df['Çıkış Zamanı'], errors='coerce').dt.strftime("%Y-%m-%d %H:%M:%S")
        
        return df
    except FileNotFoundError:
        # Return an empty DataFrame with the appropriate columns if the file doesn't exist
        print("Excel file not found. Returning empty DataFrame.")
        return pd.DataFrame(columns=["İsim", "Giriş Zamanı", "Çıkış Zamanı", "Süre"])
    except Exception as e:
        # Catch any other exceptions and display the error
        print(f"Error reading Excel file: {e}")
        return pd.DataFrame(columns=["İsim", "Giriş Zamanı", "Çıkış Zamanı", "Süre"])

# Function to add or update a record
def detayli_kayit_ekle(isim, giris=None, cikis=None, sure=None):
    df = detayli_kayitlari_oku()
    
    if df[df['İsim'] == isim].empty:
        yeni_kayit = pd.DataFrame([{"İsim": isim, "Giriş Zamanı": giris, "Çıkış Zamanı": cikis, "Süre": sure}])
        df = pd.concat([df, yeni_kayit], ignore_index=True)
    else:
        index = df[df['İsim'] == isim].index[0]
        if giris is not None:
            df.at[index, 'Giriş Zamanı'] = giris
        if cikis is not None:
            df.at[index, 'Çıkış Zamanı'] = cikis
        if sure is not None:
            df.at[index, 'Süre'] = sure

    kayitlari_excele_yaz(df)

@app.route("/")
def index():
    # Read data from the Excel file
    df = detayli_kayitlari_oku()
    
    # Fill missing values with None and convert DataFrame to a list of dictionaries
    kisiler = df.to_dict(orient='records')
    
    # Pass the processed data to the template
    return render_template("index.html", kisiler=kisiler)

@app.route('/debug')
def debug_view():
    df = detayli_kayitlari_oku()
    return df.to_html()

@app.route('/giris', methods=['POST'])
def giris_yap():
    isim = request.form.get('isim').strip()
    if not isim:
        flash("İsim alanı boş olamaz.")
        return redirect(url_for('index'))

    df = detayli_kayitlari_oku()

    # Check if the user has an entry already
    if df[df['İsim'] == isim].empty:
        simdi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        detayli_kayit_ekle(isim, giris=simdi)
        flash("Giriş işlemi başarılı.")
    else:
        index = df[df['İsim'] == isim].index[0]
        if pd.isna(df.at[index, 'Giriş Zamanı']):
            simdi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            detayli_kayit_ekle(isim, giris=simdi)
            flash("Giriş işlemi başarılı.")
        else:
            flash(f"{isim} için zaten bir giriş kaydı mevcut.")

    return redirect(url_for('index'))

@app.route('/cikis', methods=['POST'])
def cikis_yap():
    isim = request.form.get('isim').strip()
    if not isim:
        flash("İsim alanı boş olamaz.")
        return redirect(url_for('index'))

    df = detayli_kayitlari_oku()
    if not df[df['İsim'] == isim].empty:
        index = df[df['İsim'] == isim].index[0]
        if pd.notna(df.at[index, 'Giriş Zamanı']):
            if pd.isna(df.at[index, 'Çıkış Zamanı']):
                # Calculate the duration
                giris_zamani = datetime.strptime(df.at[index, 'Giriş Zamanı'], "%Y-%m-%d %H:%M:%S")
                cikis_zamani = datetime.now()
                sure = cikis_zamani - giris_zamani

                detayli_kayit_ekle(
                    isim, 
                    cikis=cikis_zamani.strftime("%Y-%m-%d %H:%M:%S"), 
                    sure=str(sure).split('.')[0]
                )
                flash(f"{isim} için çıkış işlemi başarılı.")
            else:
                flash(f"{isim} zaten çıkış yaptı.")
        else:
            flash(f"{isim} giriş yapmadan çıkış yapamaz.")
    else:
        flash("Kişi bulunamadı.")

    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)

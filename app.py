from flask import Flask, redirect, render_template, request, flash, url_for, session, jsonify
from datetime import datetime, timedelta
import pandas as pd
import os
import secrets


app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

DETAYLI_KAYIT_DOSYASI = "kayitlar.xlsx"

def excel_dosyasi_olustur():
    if not os.path.exists(DETAYLI_KAYIT_DOSYASI):
        detayli_kayit_df = pd.DataFrame(columns=["İsim", "Giriş Zamanı", "Çıkış Zamanı", "Süre"])
        detayli_kayit_df.to_excel(DETAYLI_KAYIT_DOSYASI, index=False, engine='openpyxl')


excel_dosyasi_olustur()

def kayitlari_excele_yaz(df):
    try:
        df.to_excel(DETAYLI_KAYIT_DOSYASI, index=False, engine='openpyxl')
    except Exception as e:
        print(f"Veri kaydedilirken bir hata oluştu: {e}")
        flash("Veri kaydedilirken bir hata oluştu. Lütfen tekrar deneyin.")

def detayli_kayitlari_oku():
    try:
        df = pd.read_excel(DETAYLI_KAYIT_DOSYASI, engine='openpyxl', usecols=["İsim", "Giriş Zamanı", "Çıkış Zamanı", "Süre"])
        df.columns = df.columns.str.strip()

        if 'Giriş Zamanı' in df.columns and not df['Giriş Zamanı'].isnull().all():
            df['Giriş Zamanı'] = pd.to_datetime(df['Giriş Zamanı'], errors='coerce').dt.strftime("%d-%m-%Y %H:%M:%S")
        if 'Çıkış Zamanı' in df.columns and not df['Çıkış Zamanı'].isnull().all():
            df['Çıkış Zamanı'] = pd.to_datetime(df['Çıkış Zamanı'], errors='coerce').dt.strftime("%d-%m-%Y %H:%M:%S")
        
        return df
    except FileNotFoundError:
        print("Excel file not found. Returning empty DataFrame.")
        return pd.DataFrame(columns=["İsim", "Giriş Zamanı", "Çıkış Zamanı", "Süre"])
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return pd.DataFrame(columns=["İsim", "Giriş Zamanı", "Çıkış Zamanı", "Süre"])

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
    # excelden okuma
    df = detayli_kayitlari_oku()
    
    # boş verileri none yapıp dict çevirme
    kisiler = df.to_dict(orient='records')
    
    # template e atma
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

    # todo düzel burayı herkes istediği kadar sayıda olsun
    if df[df['İsim'] == isim].empty:
        simdi = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        detayli_kayit_ekle(isim, giris=simdi)
        flash("Giriş işlemi başarılı.")
    else:
        index = df[df['İsim'] == isim].index[0]
        if pd.isna(df.at[index, 'Giriş Zamanı']):
            simdi = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
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
                # süreyi hesaplama
                giris_zamani = datetime.strptime(df.at[index, 'Giriş Zamanı'], "%d-%m-%Y %H:%M:%S")
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
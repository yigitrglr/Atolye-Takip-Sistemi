from flask import Flask, redirect, render_template, request, flash, url_for
from datetime import datetime
import pandas as pd
import os
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

DETAYLI_KAYIT_DOSYASI = "log.xlsx"

def excel_dosyasi_olustur():
    if not os.path.exists(DETAYLI_KAYIT_DOSYASI):
        pd.DataFrame(columns=["UUID", "İsim", "Giriş Zamanı", "Çıkış Zamanı", "Süre"]).to_excel(
            DETAYLI_KAYIT_DOSYASI, index=False, engine='openpyxl'
        )

excel_dosyasi_olustur()

def dosyalari_okuma():
    try:
        dfKayit = pd.read_excel(DETAYLI_KAYIT_DOSYASI, engine='openpyxl')
        return dfKayit
    except Exception as e:
        flash(f"Dosya okunurken bir hata oluştu: {e}")
        return pd.DataFrame()

def kayitlari_excele_yaz(dfKayit):
    try:
        dfKayit.to_excel(DETAYLI_KAYIT_DOSYASI, index=False, engine='openpyxl')
    except Exception as e:
        flash(f"Veri kaydedilirken bir hata oluştu: {e}")

def detayli_kayit_ekle(isim, giris=None, cikis=None, sure=None):
    dfKayit = dosyalari_okuma()
    yeni_id = secrets.token_hex(8)
    yeni_kayit = {
        "UUID": yeni_id,
        "İsim": isim,
        "Giriş Zamanı": giris,
        "Çıkış Zamanı": cikis,
        "Süre": sure,
    }
    dfKayit = pd.concat([dfKayit, pd.DataFrame([yeni_kayit])], ignore_index=True)
    kayitlari_excele_yaz(dfKayit)

@app.route("/")
def index():
    dfKayit = dosyalari_okuma()
    kisiler = dfKayit.fillna('').to_dict(orient='records')
    return render_template("index.html", kisiler=kisiler)

@app.route('/giris', methods=['POST'])
def giris_yap():
    isim = request.form.get('isim', '').strip()
    if not isim:
        flash("İsim alanı boş olamaz.")
        return redirect(url_for('index'))

    simdi = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    detayli_kayit_ekle(isim, giris=simdi)
    flash(f"{isim} için giriş işlemi başarılı.")
    return redirect(url_for('index'))

@app.route('/cikis', methods=['POST'])
def cikis_yap():
    isim = request.form.get('isim', '').strip()
    uuid = request.form.get('uuid', '').strip()

    if not isim or not uuid:
        flash("İsim veya UUID boş olamaz.")
        return redirect(url_for('index'))

    dfKayit = dosyalari_okuma()

    user_record = dfKayit[dfKayit['UUID'] == uuid]

    if not user_record.empty:
        index = user_record.index[0]
        if pd.notna(dfKayit.at[index, 'Giriş Zamanı']) and pd.isna(dfKayit.at[index, 'Çıkış Zamanı']):
            giris_zamani = datetime.strptime(dfKayit.at[index, 'Giriş Zamanı'], "%d-%m-%Y %H:%M:%S")
            cikis_zamani = datetime.now()
            sure = cikis_zamani - giris_zamani

            dfKayit.at[index, 'Çıkış Zamanı'] = cikis_zamani.strftime("%d-%m-%Y %H:%M:%S")
            dfKayit.at[index, 'Süre'] = str(sure).split('.')[0]

            kayitlari_excele_yaz(dfKayit=dfKayit)
            flash(f"{isim} için çıkış işlemi başarılı.")
        else:
            flash(f"{isim} zaten çıkış yaptı veya giriş kaydı bulunmuyor.")
    else:
        flash(f"{isim} ve UUID ({uuid}) eşleşen bir kayıt bulunamadı.")

    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)

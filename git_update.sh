#!/bin/bash

# Varsayılan uzak depo ve dal
REMOTE="origin"
BRANCH="main"

# Commit mesajı belirleme
if [ -z "$1" ]; then
  # Eğer commit mesajı verilmezse, otomatik bir mesaj oluştur
  COMMIT_MESSAGE="Otomatik güncelleme - $(date +'%Y-%m-%d %H:%M:%S')"
  echo "Commit mesajı belirtilmedi. Varsayılan mesaj kullanılacak: \"$COMMIT_MESSAGE\""
else
  # Kullanıcı tarafından sağlanan mesajı kullan
  COMMIT_MESSAGE="$1"
fi

# Uzak depo ve dal parametreleri
if [ -n "$2" ]; then
  REMOTE="$2"
fi

if [ -n "$3" ]; then
  BRANCH="$3"

fi

echo "Değişiklikler ekleniyor..."
git add .

echo "Değişiklikler commit ediliyor: \"$COMMIT_MESSAGE\""
git commit -m "$COMMIT_MESSAGE"

echo "Değişiklikler $REMOTE/$BRANCH adresine gönderiliyor..."
git push "$REMOTE" "$BRANCH"

if [ $? -eq 0 ]; then
  echo "İşlem başarıyla tamamlandı."
else
  echo "Bir hata oluştu. Lütfen yukarıdaki mesajları kontrol edin."
fi
"""
Lexis — Animasyon Yardımcıları

Süreler ve eğriler tek yerden gelir: her ekranda farklı bir hız uygulamayı
tutarsız hissettirir.

Süre seçimi: 120-260 ms aralığı, hareketin fark edildiği ama beklemeye
dönüşmediği banttır. Daha kısası göz kırpması gibi kaybolur, daha uzunu
kullanıcıyı bekletir — özellikle sayfa geçişi gibi sık tekrarlanan yerlerde.
"""

from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QWidget

# Küçük öğeler: chip, rozet, durum metni.
DURATION_FAST = 120
# Sayfa geçişi, panel açılışı — en sık görülen hareket.
DURATION_NORMAL = 180
# Dikkat çekmesi istenen, seyrek geçişler (ör. çalışma modunda cevabın açılması).
DURATION_SLOW = 260

_EFFECT_ATTR = "_lexis_fade_effect"
_ANIM_ATTR = "_lexis_fade_anim"


def fade_in(
    widget: QWidget,
    duration: int = DURATION_NORMAL,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
) -> QPropertyAnimation:
    """
    Widget'ı yumuşakça belirtir.

    Efekt ve animasyon nesneleri widget başına bir kez kurulup tekrar kullanılır.
    Her çağrıda yenisini yaratmak iki soruna yol açıyordu: önceki animasyon hâlâ
    çalışırken setGraphicsEffect eskisini sildiği için süreç çöküyor, ayrıca her
    geçişte widget'a yeni çocuk nesneler birikiyordu.
    """
    effect = _effect_for(widget)
    anim = _anim_for(widget, effect)

    # Süren bir animasyon varsa önce durdurulur, sonra baştan başlatılır.
    anim.stop()
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(easing)
    anim.start()
    return anim


def _effect_for(widget: QWidget) -> QGraphicsOpacityEffect:
    """
    Widget'ın opaklık efektini döndürür; yoksa kurar.

    Efekt animasyon bitince kapatılmıyor, kalıcı olarak açık kalıyor. Kapatmayı
    denedim ve PyQt6'da güvenli bir yolunu bulamadım: `setEnabled(False)` hem
    animasyonun `finished` sinyalinden hem de ayrı bir QTimer'dan çağrıldığında
    süreci çökertiyor; widget'ı ve efekti sip.isdeleted ile korumak da işe
    yaramadı — nesneler sip'e göre canlı görünürken çöküyor. Çağrıyı tamamen
    kaldırmak (timer'ın gövdesini boşaltmak) çökmeyi belirleyici olarak
    bitiriyor, kök neden ise PyQt6'nın içinde kaldı.

    Bedeli ölçüldü: etkin efekt widget'ı her boyamada ekran dışı tampona
    çizdiriyor ve en ağır ekranda (60 kartlık kütüphane) kare başına ~1 ms
    ekliyor — 60 fps bütçesi olan 16.7 ms'in içinde. Anlamadığım bir çökme
    riskini taşımaktansa bu ölçülü bedeli ödemek daha doğru.
    """
    effect = getattr(widget, _EFFECT_ATTR, None)
    if effect is None:
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        setattr(widget, _EFFECT_ATTR, effect)
    return effect


def _anim_for(widget: QWidget, effect: QGraphicsOpacityEffect) -> QPropertyAnimation:
    anim = getattr(widget, _ANIM_ATTR, None)
    if anim is None:
        anim = QPropertyAnimation(effect, b"opacity", widget)
        setattr(widget, _ANIM_ATTR, anim)
    return anim

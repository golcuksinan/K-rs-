import { useEffect, useState } from "react";

import parseError from "../api/parseError";


const BOS = { items: [], total: 0 };


// Liste uçlarının ortak Page zarfı + yükleniyor/hata durumu. `atla` true iken (zorunlu
// parametre henüz yoksa) istek atılmaz. Yükleniyor durumu state ile değil, gelen yanıtın
// hangi bağımlılıklara ait olduğuyla türetiliyor: effect gövdesinde setState çağrılamıyor
// (react-hooks/set-state-in-effect).
export default function usePagedList(istek, bagimliliklar, atla = false) {

    const anahtar = JSON.stringify([atla, ...bagimliliklar]);

    const [sonuc, setSonuc] = useState({ anahtar: null, sayfa: BOS, hata: "" });

    useEffect(() => {

        if (atla) {

            return;

        }

        // Arama sırasında yanıtlar sırasız dönebilir; sökülen effect'in sonucu yazılmaz.
        let iptal = false;

        istek()

            .then((res) => {

                if (!iptal) {

                    setSonuc({

                        anahtar,

                        sayfa: { items: res.data.items, total: res.data.total },

                        hata: "",

                    });

                }

            })

            .catch((error) => {

                if (!iptal) {

                    setSonuc({ anahtar, sayfa: BOS, hata: parseError(error) });

                }

            });

        return () => {

            iptal = true;

        };

        // istek her render'da yeniden kuruluyor; bağımlılıklar çağıran tarafta verilir.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [anahtar]);

    return {

        sayfa: sonuc.sayfa,

        yukleniyor: !atla && sonuc.anahtar !== anahtar,

        hata: sonuc.anahtar === anahtar ? sonuc.hata : "",

    };

}

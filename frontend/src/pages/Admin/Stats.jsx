import { useEffect, useState } from "react";

import { getEventStats, getStats } from "../../api/admin";

import parseError from "../../api/parseError";

import AdminNav from "../../components/AdminNav";
import Card from "../../components/Card";
import ErrorMessage from "../../components/Error";
import Loading from "../../components/Loading";


const GUN_SECENEKLERI = [7, 30, 90];

const ETIKETLER = {

    total: "toplam",

    verified: "doğrulanmış",

    unverified: "doğrulanmamış",

    universities: "üniversite",

    faculties: "fakülte",

    departments: "bölüm",

    courses: "ders",

    course_departments: "ders-bölüm bağı",

    professors: "hoca",

    course_professors: "ders-hoca eşleşmesi",

    courses_without_professor: "hocasız ders",

    course_departments_without_curriculum: "müfredat bilgisi eksik bağ",

    reviews_total: "toplam değerlendirme",

    reviews_with_pending_edit: "onay bekleyen düzenleme",

    reports_total: "toplam rapor",

    pending_registration_verifications: "bekleyen kayıt doğrulaması",

    pending_password_resets: "bekleyen şifre sıfırlama",

};


function Bolum({ baslik, veri }) {

    return (

        <Card className="p-6">

            <h2 className="text-xl font-semibold mb-4">

                {baslik}

            </h2>

            <dl className="space-y-1 text-sm">

                {Object.entries(veri).map(([anahtar, deger]) => (

                    <div key={anahtar} className="flex justify-between gap-6">

                        <dt className="text-gray-600">

                            {ETIKETLER[anahtar] ?? anahtar}

                        </dt>

                        <dd>

                            {typeof deger === "object" && deger !== null

                                ? Object.entries(deger)

                                    .map(([alt, sayi]) => `${alt}: ${sayi}`)

                                    .join(" · ")

                                : String(deger)}

                        </dd>

                    </div>

                ))}

            </dl>

        </Card>

    );

}


export default function Stats() {

    const [gun, setGun] = useState(30);

    // Bu iki uç Page zarfı kullanmaz; usePagedList yerine doğrudan okunuyor.
    const [ozet, setOzet] = useState({ yuklendi: false, veri: null, hata: "" });

    const [olaylar, setOlaylar] = useState({ anahtar: null, veri: null, hata: "" });


    useEffect(() => {

        let iptal = false;

        getStats()

            .then((res) => {

                if (!iptal) {

                    setOzet({ yuklendi: true, veri: res.data, hata: "" });

                }

            })

            .catch((error) => {

                if (!iptal) {

                    setOzet({ yuklendi: true, veri: null, hata: parseError(error) });

                }

            });

        return () => {

            iptal = true;

        };

    }, []);


    useEffect(() => {

        let iptal = false;

        getEventStats(gun)

            .then((res) => {

                if (!iptal) {

                    setOlaylar({ anahtar: gun, veri: res.data, hata: "" });

                }

            })

            .catch((error) => {

                if (!iptal) {

                    setOlaylar({ anahtar: gun, veri: null, hata: parseError(error) });

                }

            });

        return () => {

            iptal = true;

        };

    }, [gun]);


    const olayYukleniyor = olaylar.anahtar !== gun;

    return (

        <section className="max-w-[900px] mx-auto px-6 py-16">

            <h1 className="heading-font text-5xl mb-10">

                İstatistikler

            </h1>

            <AdminNav />

            {!ozet.yuklendi && <Loading />}

            <ErrorMessage message={ozet.hata} />

            {ozet.veri && (

                <div className="space-y-6">

                    <p className="text-sm text-gray-600">

                        {new Date(ozet.veri.generated_at).toLocaleString("tr-TR")}

                    </p>

                    <Bolum baslik="Kullanıcılar" veri={ozet.veri.users} />

                    <Bolum baslik="İçerik" veri={ozet.veri.content} />

                    <Bolum baslik="Veri sağlığı" veri={ozet.veri.data_health} />

                    <Bolum baslik="Moderasyon" veri={ozet.veri.moderation} />

                </div>

            )}

            <div className="mt-14">

                <div className="flex items-center gap-4 mb-6">

                    <h2 className="text-2xl font-semibold">

                        Olaylar

                    </h2>

                    <select
                        className="border p-2"
                        value={gun}
                        onChange={(e) => setGun(Number(e.target.value))}
                    >

                        {GUN_SECENEKLERI.map((secenek) => (

                            <option key={secenek} value={secenek}>

                                son {secenek} gün

                            </option>

                        ))}

                    </select>

                </div>

                {olayYukleniyor && <Loading />}

                <ErrorMessage message={olaylar.hata} />

                {olaylar.veri && (

                    <Card className="p-6">

                        {!olaylar.veri.first_recorded_day && (

                            <p className="text-sm text-gray-600 mb-4">

                                Sayaçlar henüz hiç veri kaydetmedi.

                            </p>

                        )}

                        <dl className="space-y-1 text-sm">

                            {olaylar.veri.events.map((olay) => (

                                <div key={olay} className="flex justify-between gap-6">

                                    <dt className="text-gray-600">

                                        {olay}

                                    </dt>

                                    <dd>

                                        {olaylar.veri.totals[olay]}

                                    </dd>

                                </div>

                            ))}

                        </dl>

                    </Card>

                )}

            </div>

        </section>

    );

}

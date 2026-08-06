import { useState } from "react";

import { getPendingReports, setReportStatus } from "../../api/admin";

import parseError from "../../api/parseError";

import usePagedList from "../../hooks/usePagedList";

import AdminNav from "../../components/AdminNav";
import Card from "../../components/Card";
import ErrorMessage from "../../components/Error";
import Loading from "../../components/Loading";
import Pagination from "../../components/Pagination";


const LIMIT = 20;


export default function Reports() {

    const [offset, setOffset] = useState(0);

    const [tetik, setTetik] = useState(0);

    const [islemHatasi, setIslemHatasi] = useState("");

    const { sayfa, yukleniyor, hata } = usePagedList(

        () => getPendingReports({ limit: LIMIT, offset }),

        [offset, tetik]

    );


    // Rapor durumları review'unkilerden farklı: resolved / dismissed.
    const karar = (id, durum) => {

        setIslemHatasi("");

        setReportStatus(id, durum)

            .then(() => setTetik((sayi) => sayi + 1))

            .catch((error) => setIslemHatasi(parseError(error)));

    };


    return (

        <section className="max-w-[900px] mx-auto px-6 py-16">

            <h1 className="heading-font text-5xl mb-10">

                Raporlar

            </h1>

            <AdminNav />

            {yukleniyor && <Loading />}

            <ErrorMessage message={hata} />

            <ErrorMessage message={islemHatasi} />

            {!yukleniyor && !hata && sayfa.items.length === 0 && (

                <p className="text-gray-600">

                    Bekleyen rapor yok.

                </p>

            )}

            <div className="space-y-6">

                {sayfa.items.map((rapor) => (

                    <Card key={rapor.id} className="p-6">

                        <p className="text-sm text-gray-600">

                            #{rapor.id} · değerlendirme {rapor.review_id} ·{" "}

                            {new Date(rapor.created_at).toLocaleDateString("tr-TR")}

                        </p>

                        <p className="mt-3 whitespace-pre-line">

                            {rapor.reason}

                        </p>

                        <div className="flex gap-3 mt-6">

                            <button
                                className="bg-[#102744] text-white px-5 py-2 text-sm"
                                onClick={() => karar(rapor.id, "resolved")}
                            >

                                Çözüldü

                            </button>

                            <button
                                className="border px-5 py-2 text-sm"
                                onClick={() => karar(rapor.id, "dismissed")}
                            >

                                Reddet

                            </button>

                        </div>

                    </Card>

                ))}

            </div>

            <Pagination
                total={sayfa.total}
                limit={LIMIT}
                offset={offset}
                onChange={setOffset}
            />

        </section>

    );

}

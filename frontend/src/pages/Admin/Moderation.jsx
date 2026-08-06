import { useState } from "react";

import { getPendingReviews, setReviewEditStatus, setReviewStatus } from "../../api/admin";

import { getReviews } from "../../api/reviews";

import parseError from "../../api/parseError";

import usePagedList from "../../hooks/usePagedList";

import AdminNav from "../../components/AdminNav";
import Card from "../../components/Card";
import ErrorMessage from "../../components/Error";
import Loading from "../../components/Loading";
import Pagination from "../../components/Pagination";


const LIMIT = 20;

const SEKMELER = [

    ["pending", "Bekleyenler"],

    ["rejected", "Reddedilenler"],

];


function Skorlar({ teaching, difficulty, fairness }) {

    return (

        <p className="text-sm">

            Anlatım {teaching} · Zorluk {difficulty} · Adalet {fairness}

        </p>

    );

}


export default function Moderation() {

    const [sekme, setSekme] = useState("pending");

    const [offset, setOffset] = useState(0);

    const [tetik, setTetik] = useState(0);

    const [islemHatasi, setIslemHatasi] = useState("");

    const { sayfa, yukleniyor, hata } = usePagedList(

        () =>

            sekme === "pending"

                ? getPendingReviews({ limit: LIMIT, offset })

                : getReviews({ status: "rejected", limit: LIMIT, offset }),

        [sekme, offset, tetik]

    );


    const sekmeDegisti = (yeni) => {

        setSekme(yeni);

        setOffset(0);

        setIslemHatasi("");

    };


    const karar = (istek) => {

        setIslemHatasi("");

        istek

            .then(() => setTetik((sayi) => sayi + 1))

            .catch((error) => setIslemHatasi(parseError(error)));

    };


    return (

        <section className="max-w-[900px] mx-auto px-6 py-16">

            <h1 className="heading-font text-5xl mb-10">

                Moderasyon

            </h1>

            <AdminNav />

            <div className="flex gap-4 mb-8">

                {SEKMELER.map(([deger, etiket]) => (

                    <button
                        key={deger}
                        className={`px-5 py-2 border ${sekme === deger ? "bg-[#102744] text-white" : ""}`}
                        onClick={() => sekmeDegisti(deger)}
                    >

                        {etiket}

                    </button>

                ))}

            </div>

            {yukleniyor && <Loading />}

            <ErrorMessage message={hata} />

            <ErrorMessage message={islemHatasi} />

            {!yukleniyor && !hata && sayfa.items.length === 0 && (

                <p className="text-gray-600">

                    Kuyruk boş.

                </p>

            )}

            <div className="space-y-6">

                {sayfa.items.map((yorum) => (

                    <Card key={yorum.id} className="p-6">

                        <p className="text-sm text-gray-600 mb-3">

                            #{yorum.id} · eşleşme {yorum.course_professor_id} ·{" "}

                            {new Date(yorum.created_at).toLocaleDateString("tr-TR")} · {yorum.status}

                        </p>

                        {yorum.has_pending_edit ? (

                            <div className="grid gap-6 md:grid-cols-2">

                                <div>

                                    <p className="text-sm text-gray-600 mb-2">

                                        Yayındaki hali

                                    </p>

                                    <Skorlar
                                        teaching={yorum.teaching_score}
                                        difficulty={yorum.difficulty_score}
                                        fairness={yorum.fairness_score}
                                    />

                                    {yorum.comment && (

                                        <p className="mt-2 whitespace-pre-line">

                                            {yorum.comment}

                                        </p>

                                    )}

                                </div>

                                <div>

                                    <p className="text-sm text-gray-600 mb-2">

                                        Önerilen hali

                                    </p>

                                    <Skorlar
                                        teaching={yorum.pending_teaching_score}
                                        difficulty={yorum.pending_difficulty_score}
                                        fairness={yorum.pending_fairness_score}
                                    />

                                    {yorum.pending_comment && (

                                        <p className="mt-2 whitespace-pre-line">

                                            {yorum.pending_comment}

                                        </p>

                                    )}

                                </div>

                            </div>

                        ) : (

                            <>

                                <Skorlar
                                    teaching={yorum.teaching_score}
                                    difficulty={yorum.difficulty_score}
                                    fairness={yorum.fairness_score}
                                />

                                {yorum.comment && (

                                    <p className="mt-3 whitespace-pre-line">

                                        {yorum.comment}

                                    </p>

                                )}

                            </>

                        )}

                        {yorum.has_pending_edit ? (

                            <div className="flex gap-3 mt-6">

                                <button
                                    className="bg-[#102744] text-white px-5 py-2 text-sm"
                                    onClick={() => karar(setReviewEditStatus(yorum.id, "approved"))}
                                >

                                    Düzenlemeyi onayla

                                </button>

                                <button
                                    className="border px-5 py-2 text-sm"
                                    onClick={() => karar(setReviewEditStatus(yorum.id, "rejected"))}
                                >

                                    Düzenlemeyi reddet

                                </button>

                            </div>

                        ) : (

                            <div className="flex gap-3 mt-6">

                                <button
                                    className="bg-[#102744] text-white px-5 py-2 text-sm"
                                    onClick={() => karar(setReviewStatus(yorum.id, "approved"))}
                                >

                                    Onayla

                                </button>

                                {yorum.status !== "rejected" && (

                                    <button
                                        className="border px-5 py-2 text-sm"
                                        onClick={() => karar(setReviewStatus(yorum.id, "rejected"))}
                                    >

                                        Reddet

                                    </button>

                                )}

                            </div>

                        )}

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

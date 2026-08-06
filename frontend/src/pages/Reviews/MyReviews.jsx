import { useEffect, useState } from "react";

import { deleteReview, getMyReviews, updateReview } from "../../api/reviews";

import parseError from "../../api/parseError";

import usePagedList from "../../hooks/usePagedList";

import Card from "../../components/Card";
import ErrorMessage from "../../components/Error";
import Loading from "../../components/Loading";
import Pagination from "../../components/Pagination";


const LIMIT = 10;

const MAX_YORUM = 1000;

const SKORLAR = [1, 2, 3, 4, 5];

const DURUM = {

    pending: "incelemede",

    approved: "yayında",

    rejected: "reddedildi",

};

// Moderasyon arka planda çalışıyor ve bildirim kanalı yok; sayfa sınırlı sayıda yenilenir.
const MAX_YOKLAMA = 5;

const YOKLAMA_ARALIGI = 5000;


export default function MyReviews() {

    const [offset, setOffset] = useState(0);

    const [tetik, setTetik] = useState(0);

    const [yoklama, setYoklama] = useState(0);

    const [duzenlenen, setDuzenlenen] = useState(null);

    const [form, setForm] = useState(null);

    const [islemHatasi, setIslemHatasi] = useState("");

    const { sayfa, yukleniyor, hata } = usePagedList(

        () => getMyReviews({ limit: LIMIT, offset }),

        [offset, tetik]

    );

    const bekleyenVar = sayfa.items.some((yorum) => yorum.status === "pending");


    useEffect(() => {

        if (!bekleyenVar || yoklama >= MAX_YOKLAMA) {

            return;

        }

        const zamanlayici = setTimeout(() => {

            setYoklama((sayi) => sayi + 1);

            setTetik((sayi) => sayi + 1);

        }, YOKLAMA_ARALIGI);

        return () => clearTimeout(zamanlayici);

    }, [bekleyenVar, yoklama, tetik]);


    const yenile = () => {

        setYoklama(0);

        setTetik((sayi) => sayi + 1);

    };


    const duzenlemeyeBasla = (yorum) => {

        setIslemHatasi("");

        setDuzenlenen(yorum.id);

        setForm({

            teaching_score: yorum.teaching_score,

            difficulty_score: yorum.difficulty_score,

            fairness_score: yorum.fairness_score,

            comment: yorum.comment ?? "",

        });

    };


    const kaydet = (e) => {

        e.preventDefault();

        setIslemHatasi("");

        updateReview(duzenlenen, {

            teaching_score: Number(form.teaching_score),

            difficulty_score: Number(form.difficulty_score),

            fairness_score: Number(form.fairness_score),

            comment: form.comment.trim() || undefined,

        })

            .then(() => {

                setDuzenlenen(null);

                yenile();

            })

            .catch((error) => setIslemHatasi(parseError(error)));

    };


    const sil = (id) => {

        if (!window.confirm("Bu değerlendirme silinsin mi?")) {

            return;

        }

        setIslemHatasi("");

        deleteReview(id)

            .then(yenile)

            .catch((error) => setIslemHatasi(parseError(error)));

    };


    return (

        <section className="max-w-[900px] mx-auto px-6 py-16">

            <h1 className="heading-font text-5xl mb-10">

                Yorumlarım

            </h1>

            {yukleniyor && <Loading />}

            <ErrorMessage message={hata} />

            <ErrorMessage message={islemHatasi} />

            {!yukleniyor && !hata && sayfa.items.length === 0 && (

                <p className="text-gray-600">

                    Henüz değerlendirme yapmadınız.

                </p>

            )}

            <div className="space-y-6">

                {sayfa.items.map((yorum) => (

                    <Card key={yorum.id} className="p-6">

                        <p className="text-sm text-gray-600">

                            {DURUM[yorum.status] ?? yorum.status}

                            {yorum.has_pending_edit && " · değişiklik onay bekliyor"}

                        </p>

                        <p className="mt-2 text-sm">

                            Anlatım {yorum.teaching_score} ·
                            Zorluk {yorum.difficulty_score} ·
                            Adalet {yorum.fairness_score}

                        </p>

                        {yorum.comment && (

                            <p className="mt-3 whitespace-pre-line">

                                {yorum.comment}

                            </p>

                        )}

                        {yorum.has_pending_edit && (

                            <div className="mt-4 border-t pt-4 text-sm">

                                <p className="text-gray-600 mb-2">

                                    Onay bekleyen hali:

                                </p>

                                <p>

                                    Anlatım {yorum.pending_teaching_score} ·
                                    Zorluk {yorum.pending_difficulty_score} ·
                                    Adalet {yorum.pending_fairness_score}

                                </p>

                                {yorum.pending_comment && (

                                    <p className="mt-2 whitespace-pre-line">

                                        {yorum.pending_comment}

                                    </p>

                                )}

                            </div>

                        )}

                        {duzenlenen === yorum.id ? (

                            <form onSubmit={kaydet} className="mt-6 space-y-4">

                                <p className="text-sm text-gray-600">

                                    {yorum.status === "approved"

                                        ? "Yayındaki hali değişmez; düzenlemeniz admin onayına düşer."

                                        : "Düzenleme doğrudan uygulanır ve yeniden moderasyona girer."}

                                </p>

                                {[

                                    ["teaching_score", "Anlatım"],

                                    ["difficulty_score", "Zorluk"],

                                    ["fairness_score", "Adalet"],

                                ].map(([alan, etiket]) => (

                                    <label key={alan} className="block">

                                        <span className="block mb-1 text-sm">

                                            {etiket}

                                        </span>

                                        <select
                                            className="w-full border p-2"
                                            value={form[alan]}
                                            onChange={(e) => setForm({ ...form, [alan]: e.target.value })}
                                        >

                                            {SKORLAR.map((skor) => (

                                                <option key={skor} value={skor}>
                                                    {skor}
                                                </option>

                                            ))}

                                        </select>

                                    </label>

                                ))}

                                <textarea
                                    className="w-full border p-3 h-28"
                                    maxLength={MAX_YORUM}
                                    value={form.comment}
                                    onChange={(e) => setForm({ ...form, comment: e.target.value })}
                                />

                                <div className="flex gap-3">

                                    <button className="bg-[#102744] text-white px-6 py-2">

                                        Kaydet

                                    </button>

                                    <button
                                        type="button"
                                        className="border px-6 py-2"
                                        onClick={() => setDuzenlenen(null)}
                                    >

                                        Vazgeç

                                    </button>

                                </div>

                            </form>

                        ) : (

                            <div className="flex gap-4 mt-4 text-sm">

                                <button className="underline" onClick={() => duzenlemeyeBasla(yorum)}>

                                    Düzenle

                                </button>

                                <button className="underline" onClick={() => sil(yorum.id)}>

                                    Sil

                                </button>

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

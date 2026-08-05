import { useState } from "react";

import { Link, useSearchParams } from "react-router-dom";

import { createReview } from "../../api/reviews";

import { getCourses } from "../../api/courses";

import { getCourseProfessors } from "../../api/courseProfessors";

import parseError from "../../api/parseError";

import useDebounce from "../../hooks/useDebounce";
import usePagedList from "../../hooks/usePagedList";

import ErrorMessage from "../../components/Error";
import Loading from "../../components/Loading";


const MIN_ARAMA = 2;

const MAX_YORUM = 2000;

const SKORLAR = [1, 2, 3, 4, 5];


export default function CreateReview() {

    const [queryParams] = useSearchParams();

    const [eslesmeId, setEslesmeId] = useState(() => queryParams.get("course_professor_id") ?? "");

    const [dersId, setDersId] = useState("");

    const [arama, setArama] = useState("");

    const gecikmeliArama = useDebounce(arama);

    const [form, setForm] = useState({

        teaching_score: 3,

        difficulty_score: 3,

        fairness_score: 3,

        comment: "",

    });

    const [hata, setHata] = useState("");

    const [gonderiliyor, setGonderiliyor] = useState(false);

    const [gonderildi, setGonderildi] = useState(false);

    const terim = gecikmeliArama.trim();

    const aramaYeterli = terim.length >= MIN_ARAMA;

    const dersler = usePagedList(

        () => getCourses({ search: terim, limit: 20 }),

        [terim],

        !aramaYeterli

    );

    const eslesmeler = usePagedList(

        () => getCourseProfessors({ course_id: dersId, limit: 100 }),

        [dersId],

        !dersId

    );


    const submit = (e) => {

        e.preventDefault();

        setHata("");

        if (!eslesmeId) {

            setHata("Önce ders ve hoca seçin");

            return;

        }

        setGonderiliyor(true);

        createReview({

            course_professor_id: Number(eslesmeId),

            teaching_score: Number(form.teaching_score),

            difficulty_score: Number(form.difficulty_score),

            fairness_score: Number(form.fairness_score),

            comment: form.comment.trim() || undefined,

        })

            // 201 dönse de yorum "pending"; AI moderasyonu arka planda çalışıyor.
            .then(() => setGonderildi(true))

            .catch((error) => setHata(parseError(error)))

            .finally(() => setGonderiliyor(false));

    };


    if (gonderildi) {

        return (

            <section className="max-w-xl mx-auto px-6 py-16">

                <h1 className="heading-font text-4xl mb-6">

                    Yorumunuz incelemede

                </h1>

                <p className="mb-8">

                    Değerlendirmeniz moderasyondan geçtikten sonra yayımlanacak.

                </p>

                <Link to="/yorumlarim" className="underline">

                    Yorumlarım

                </Link>

            </section>

        );

    }

    return (

        <section className="max-w-xl mx-auto px-6 py-16">

            <h1 className="heading-font text-4xl mb-8">

                Yorum Yap

            </h1>

            {!queryParams.get("course_professor_id") && (

                <div className="mb-10 space-y-4">

                    <input
                        className="w-full border p-3"
                        placeholder="Ders adı veya kodu ara"
                        value={arama}
                        onChange={(e) => setArama(e.target.value)}
                    />

                    {dersler.yukleniyor && <Loading />}

                    <ErrorMessage message={dersler.hata} />

                    {aramaYeterli && (

                        <select
                            className="w-full border p-3"
                            value={dersId}
                            onChange={(e) => {

                                setDersId(e.target.value);

                                setEslesmeId("");

                            }}
                        >

                            <option value="">Ders seçin</option>

                            {dersler.sayfa.items.map((ders) => (

                                <option key={ders.id} value={ders.id}>
                                    {ders.code} — {ders.name}
                                </option>

                            ))}

                        </select>

                    )}

                    {dersId && (

                        <select
                            className="w-full border p-3"
                            value={eslesmeId}
                            onChange={(e) => setEslesmeId(e.target.value)}
                        >

                            <option value="">Hoca / dönem seçin</option>

                            {eslesmeler.sayfa.items.map((eslesme) => (

                                <option key={eslesme.id} value={eslesme.id}>
                                    {eslesme.professor_name} — {eslesme.term}
                                </option>

                            ))}

                        </select>

                    )}

                    <ErrorMessage message={eslesmeler.hata} />

                </div>

            )}

            <form onSubmit={submit} className="space-y-5">

                {[

                    ["teaching_score", "Anlatım"],

                    ["difficulty_score", "Zorluk"],

                    ["fairness_score", "Adalet"],

                ].map(([alan, etiket]) => (

                    <label key={alan} className="block">

                        <span className="block mb-1">

                            {etiket}

                        </span>

                        <select
                            className="w-full border p-3"
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

                <label className="block">

                    <span className="block mb-1">

                        Yorum (isteğe bağlı)

                    </span>

                    <textarea
                        className="w-full border p-3 h-32"
                        maxLength={MAX_YORUM}
                        value={form.comment}
                        onChange={(e) => setForm({ ...form, comment: e.target.value })}
                    />

                    <span className="text-sm text-gray-600">

                        {form.comment.length} / {MAX_YORUM}

                    </span>

                </label>

                <button
                    className="bg-[#102744] text-white px-8 py-3 disabled:opacity-60"
                    disabled={gonderiliyor}
                >

                    Gönder

                </button>

            </form>

            <ErrorMessage message={hata} />

        </section>

    );

}

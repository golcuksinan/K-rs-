import { useEffect, useState } from "react";

import { Link, useParams } from "react-router-dom";

import { getProfessor } from "../../api/professors";

import { getReviews } from "../../api/reviews";

import parseError from "../../api/parseError";

import usePagedList from "../../hooks/usePagedList";

import Card from "../../components/Card";
import ErrorMessage from "../../components/Error";
import Loading from "../../components/Loading";
import Pagination from "../../components/Pagination";
import Rating from "../../components/Rating";
import ReviewCard from "../../components/ReviewCard";


const YORUM_LIMIT = 10;

const DERS_LIMIT = 6;


export default function ProfessorDetail() {

    const { id } = useParams();

    const [sonuc, setSonuc] = useState({ anahtar: null, hoca: null, hata: "" });

    // Ders başına seçili dönem: "Yorum yap" tek bir course_professor_id istiyor.
    const [donemler, setDonemler] = useState({});

    const [tumDersler, setTumDersler] = useState(false);

    const [offset, setOffset] = useState(0);


    useEffect(() => {

        let iptal = false;

        getProfessor(id)

            .then((res) => {

                if (!iptal) {

                    setSonuc({ anahtar: id, hoca: res.data, hata: "" });

                }

            })

            .catch((error) => {

                if (!iptal) {

                    setSonuc({ anahtar: id, hoca: null, hata: parseError(error) });

                }

            });

        return () => {

            iptal = true;

        };

    }, [id]);


    // Detay ucu yorum döndürmüyor, yorumlar ayrı istekle geliyor (sözleşme §5).
    const yorumlar = usePagedList(

        () => getReviews({

            professor_id: id,

            limit: YORUM_LIMIT,

            offset,

        }),

        [id, offset]

    );

    const yukleniyor = sonuc.anahtar !== id;

    const hoca = sonuc.hoca;


    if (yukleniyor) {

        return <Loading />;

    }

    if (!hoca) {

        return <ErrorMessage message={sonuc.hata || "Hoca bulunamadı"} />;

    }

    // Yorumlar hocanın tüm derslerinden geliyor; ReviewResponse ders/dönem taşımadığı için
    // etiket course_professor_id üzerinden burada eşleştirilir.
    const etiketler = {};

    hoca.courses.forEach((ders) => ders.terms.forEach((donem) => {

        etiketler[donem.course_professor_id] = `${ders.course_name} · ${donem.term}`;

    }));

    // Hoca başına ortalama 7, en fazla 39 ders var; hepsi basılınca yorumlar ekranlarca aşağıda
    // kalıyor. Kısa listede en çok yorum alan dersler görünsün.
    const siraliDersler = [...hoca.courses].sort((a, b) => (

        b.review_count - a.review_count || a.course_name.localeCompare(b.course_name, "tr")

    ));

    const gosterilenDersler = tumDersler ? siraliDersler : siraliDersler.slice(0, DERS_LIMIT);

    return (

        <section className="max-w-[1200px] mx-auto px-6 py-16">

            <h1 className="heading-font text-5xl">

                {hoca.full_name}

            </h1>

            <h2 className="heading-font text-3xl mt-10 mb-6">

                Dersler

            </h2>

            {hoca.courses.length === 0 && (

                <p className="text-gray-600">

                    Bu hoca için ders kaydı yok.

                </p>

            )}

            <div className="grid md:grid-cols-2 gap-6">

                {gosterilenDersler.map((ders) => {

                    const seciliDonem = donemler[ders.course_id] ?? ders.terms[0].course_professor_id;

                    return (

                        <Card key={ders.course_id} className="p-6">

                            <Link
                                to={`/hocalar/${id}/dersler/${seciliDonem}`}
                                className="text-xl font-semibold underline"
                            >

                                {ders.course_name}

                            </Link>

                            <p className="text-gray-600 text-sm mt-1 mb-4">

                                {ders.course_code} · {ders.review_count} değerlendirme

                            </p>

                            <div className="flex flex-wrap gap-2 mb-4">

                                {ders.terms.map((donem) => (

                                    <span
                                        key={donem.course_professor_id}
                                        className="border px-2 py-1 text-xs"
                                    >

                                        {donem.term}

                                    </span>

                                ))}

                            </div>

                            <Rating
                                teaching={ders.average_teaching_score}
                                difficulty={ders.average_difficulty_score}
                                fairness={ders.average_fairness_score}
                            />

                            <p className="mt-4 flex items-center gap-3">

                                {ders.terms.length > 1 && (

                                    <select
                                        className="border p-1 text-sm"
                                        value={seciliDonem}
                                        onChange={(e) => setDonemler({
                                            ...donemler,
                                            [ders.course_id]: Number(e.target.value),
                                        })}
                                    >

                                        {ders.terms.map((donem) => (

                                            <option
                                                key={donem.course_professor_id}
                                                value={donem.course_professor_id}
                                            >

                                                {donem.term}

                                            </option>

                                        ))}

                                    </select>

                                )}

                                <Link
                                    to={`/yorum-yap?course_professor_id=${seciliDonem}`}
                                    className="underline text-sm"
                                >

                                    Yorum yap

                                </Link>

                            </p>

                        </Card>

                    );

                })}

            </div>

            {hoca.courses.length > DERS_LIMIT && (

                <button
                    className="underline text-sm mt-6"
                    onClick={() => setTumDersler(!tumDersler)}
                >

                    {tumDersler

                        ? "Dersleri gizle"

                        : `Tüm dersleri göster (${hoca.courses.length})`}

                </button>

            )}

            <h2 className="heading-font text-3xl mt-12 mb-6">

                Yorumlar

            </h2>

            {yorumlar.yukleniyor && <Loading />}

            <ErrorMessage message={yorumlar.hata} />

            {!yorumlar.yukleniyor && !yorumlar.hata && yorumlar.sayfa.items.length === 0 && (

                <p className="text-gray-600">

                    Yayımlanmış yorum yok.

                </p>

            )}

            <div className="space-y-6">

                {yorumlar.sayfa.items.map((yorum) => (

                    <ReviewCard
                        key={yorum.id}
                        review={yorum}
                        etiket={etiketler[yorum.course_professor_id]}
                    />

                ))}

            </div>

            <Pagination
                total={yorumlar.sayfa.total}
                limit={YORUM_LIMIT}
                offset={offset}
                onChange={setOffset}
            />

        </section>

    );

}

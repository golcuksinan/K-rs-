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


export default function ProfessorDetail() {

    const { id } = useParams();

    const [sonuc, setSonuc] = useState({ anahtar: null, hoca: null, hata: "" });

    const [secili, setSecili] = useState(null);

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

            course_professor_id: secili || undefined,

            limit: YORUM_LIMIT,

            offset,

        }),

        [id, secili, offset]

    );

    const yukleniyor = sonuc.anahtar !== id;

    const hoca = sonuc.hoca;


    const dersSec = (cpId) => {

        setSecili(secili === cpId ? null : cpId);

        setOffset(0);

    };


    if (yukleniyor) {

        return <Loading />;

    }

    if (!hoca) {

        return <ErrorMessage message={sonuc.hata || "Hoca bulunamadı"} />;

    }

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

                {hoca.courses.map((ders) => (

                    <Card
                        key={ders.id}
                        className={`p-6 ${secili === ders.id ? "border-2" : ""}`}
                    >

                        <button
                            className="text-xl font-semibold text-left w-full"
                            onClick={() => dersSec(ders.id)}
                        >

                            {ders.course_name}

                        </button>

                        <p className="text-gray-600 text-sm mt-1 mb-4">

                            {ders.course_code} · {ders.term} · {ders.review_count} değerlendirme

                        </p>

                        <Rating
                            teaching={ders.average_teaching_score}
                            difficulty={ders.average_difficulty_score}
                            fairness={ders.average_fairness_score}
                        />

                        <p className="mt-4">

                            <Link
                                to={`/yorum-yap?course_professor_id=${ders.id}`}
                                className="underline text-sm"
                            >

                                Yorum yap

                            </Link>

                        </p>

                    </Card>

                ))}

            </div>

            <h2 className="heading-font text-3xl mt-12 mb-6">

                Yorumlar

            </h2>

            {secili && (

                <p className="mb-6 text-sm">

                    Seçili ders için filtrelendi.{" "}

                    <button className="underline" onClick={() => dersSec(secili)}>

                        Tüm yorumlar

                    </button>

                </p>

            )}

            {yorumlar.yukleniyor && <Loading />}

            <ErrorMessage message={yorumlar.hata} />

            {!yorumlar.yukleniyor && !yorumlar.hata && yorumlar.sayfa.items.length === 0 && (

                <p className="text-gray-600">

                    Yayımlanmış yorum yok.

                </p>

            )}

            <div className="space-y-6">

                {yorumlar.sayfa.items.map((yorum) => (

                    <ReviewCard key={yorum.id} review={yorum} />

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

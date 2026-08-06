import { useEffect, useState } from "react";

import { Link, useParams } from "react-router-dom";

import { getCourseProfessor } from "../../api/courseProfessors";

import { getReviews } from "../../api/reviews";

import parseError from "../../api/parseError";

import usePagedList from "../../hooks/usePagedList";

import ErrorMessage from "../../components/Error";
import Loading from "../../components/Loading";
import Pagination from "../../components/Pagination";
import Rating from "../../components/Rating";
import ReviewCard from "../../components/ReviewCard";


const YORUM_LIMIT = 10;


export default function CourseProfessorDetail() {

    const { professorId, courseProfessorId } = useParams();

    const [sonuc, setSonuc] = useState({ anahtar: null, eslesme: null, hata: "" });

    const [offset, setOffset] = useState(0);


    useEffect(() => {

        let iptal = false;

        getCourseProfessor(courseProfessorId)

            .then((res) => {

                if (!iptal) {

                    setSonuc({ anahtar: courseProfessorId, eslesme: res.data, hata: "" });

                }

            })

            .catch((error) => {

                if (!iptal) {

                    setSonuc({ anahtar: courseProfessorId, eslesme: null, hata: parseError(error) });

                }

            });

        return () => {

            iptal = true;

        };

    }, [courseProfessorId]);


    const yorumlar = usePagedList(

        () => getReviews({

            course_professor_id: courseProfessorId,

            limit: YORUM_LIMIT,

            offset,

        }),

        [courseProfessorId, offset]

    );

    const yukleniyor = sonuc.anahtar !== courseProfessorId;

    const eslesme = sonuc.eslesme;


    if (yukleniyor) {

        return <Loading />;

    }

    if (!eslesme) {

        return <ErrorMessage message={sonuc.hata || "Ders/hoca eşleşmesi bulunamadı"} />;

    }

    return (

        <section className="max-w-[1200px] mx-auto px-6 py-16">

            <Link to={`/hocalar/${professorId}`} className="underline text-sm">

                {eslesme.professor_name}

            </Link>

            <h1 className="heading-font text-5xl mt-2">

                {eslesme.course_name}

            </h1>

            <p className="text-gray-600 mt-2">

                {eslesme.course_code} · {eslesme.term} · {eslesme.review_count} değerlendirme

            </p>

            <div className="mt-6">

                <Rating
                    teaching={eslesme.average_teaching_score}
                    difficulty={eslesme.average_difficulty_score}
                    fairness={eslesme.average_fairness_score}
                />

            </div>

            <p className="mt-6">

                <Link
                    to={`/yorum-yap?course_professor_id=${eslesme.id}`}
                    className="underline text-sm"
                >

                    Yorum yap

                </Link>

            </p>

            <h2 className="heading-font text-3xl mt-12 mb-6">

                Yorumlar

            </h2>

            {yorumlar.yukleniyor && <Loading />}

            <ErrorMessage message={yorumlar.hata} />

            {!yorumlar.yukleniyor && !yorumlar.hata && yorumlar.sayfa.items.length === 0 && (

                <p className="text-gray-600">

                    Bu ders/dönem için yayımlanmış yorum yok.

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

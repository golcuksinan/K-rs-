import { useEffect, useState } from "react";

import { Link, useLocation, useParams } from "react-router-dom";

import { getCourseProfessor, getCourseProfessors } from "../../api/courseProfessors";

import { getReviews } from "../../api/reviews";

import usePagedList from "../../hooks/usePagedList";

import Card from "../../components/Card";
import ErrorMessage from "../../components/Error";
import Loading from "../../components/Loading";
import Pagination from "../../components/Pagination";
import Rating from "../../components/Rating";
import ReviewCard from "../../components/ReviewCard";


const YORUM_LIMIT = 10;


export default function CourseDetail() {

    const { id } = useParams();

    const location = useLocation();

    const [ders, setDers] = useState(() => location.state?.ders ?? null);

    const [secili, setSecili] = useState(null);

    const [offset, setOffset] = useState(0);

    // term verilmezse backend en son dönemi seçer; dönem listesi veren bir uç yok.
    const hocalar = usePagedList(

        () => getCourseProfessors({ course_id: id, limit: 100 }),

        [id]

    );

    const yorumlar = usePagedList(

        () => getReviews({ course_professor_id: secili, limit: YORUM_LIMIT, offset }),

        [secili, offset],

        !secili

    );


    // Ders detay ucu yok: ad/kod liste sayfasından taşınmadıysa eşleşme detayından okunur.
    useEffect(() => {

        const ilk = hocalar.sayfa.items[0];

        if (ders || !ilk) {

            return;

        }

        getCourseProfessor(ilk.id)

            .then((res) => setDers({ name: res.data.course_name, code: res.data.course_code }))

            .catch(() => {});

    }, [ders, hocalar.sayfa.items]);


    const hocaSec = (cpId) => {

        setSecili(cpId);

        setOffset(0);

    };


    return (

        <section className="max-w-[1200px] mx-auto px-6 py-16">

            <h1 className="heading-font text-5xl">

                {ders?.name ?? "Ders"}

            </h1>

            {ders?.code && (

                <p className="text-gray-600 mt-2">

                    {ders.code}

                </p>

            )}

            <h2 className="heading-font text-3xl mt-10 mb-6">

                Hocalar

            </h2>

            {hocalar.yukleniyor && <Loading />}

            <ErrorMessage message={hocalar.hata} />

            {!hocalar.yukleniyor && !hocalar.hata && hocalar.sayfa.items.length === 0 && (

                <p className="text-gray-600">

                    Bu ders için hoca kaydı yok.

                </p>

            )}

            <div className="grid md:grid-cols-2 gap-6">

                {hocalar.sayfa.items.map((eslesme) => (

                    <Card
                        key={eslesme.id}
                        className={`p-6 ${secili === eslesme.id ? "border-2" : ""}`}
                    >

                        <button
                            className="text-xl font-semibold text-left w-full"
                            onClick={() => hocaSec(eslesme.id)}
                        >

                            {eslesme.professor_name}

                        </button>

                        <p className="text-gray-600 text-sm mt-1 mb-4">

                            {eslesme.term}

                        </p>

                        <Rating
                            teaching={eslesme.avg_teaching}
                            difficulty={eslesme.avg_difficulty}
                            fairness={eslesme.avg_fairness}
                        />

                        <p className="mt-4">

                            <Link
                                to={`/yorum-yap?course_professor_id=${eslesme.id}`}
                                className="underline text-sm"
                            >

                                Yorum yap

                            </Link>

                        </p>

                    </Card>

                ))}

            </div>

            {secili && (

                <>

                    <h2 className="heading-font text-3xl mt-12 mb-6">

                        Yorumlar

                    </h2>

                    {yorumlar.yukleniyor && <Loading />}

                    <ErrorMessage message={yorumlar.hata} />

                    {!yorumlar.yukleniyor && !yorumlar.hata && yorumlar.sayfa.items.length === 0 && (

                        <p className="text-gray-600">

                            Bu hoca/dönem için yayımlanmış yorum yok.

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

                </>

            )}

        </section>

    );

}

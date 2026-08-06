import { useState } from "react";

import { Link, useSearchParams } from "react-router-dom";

import { getProfessors } from "../../api/professors";

import useDebounce from "../../hooks/useDebounce";
import usePagedList from "../../hooks/usePagedList";

import Card from "../../components/Card";
import ErrorMessage from "../../components/Error";
import Loading from "../../components/Loading";
import Pagination from "../../components/Pagination";


const LIMIT = 24;


export default function Professors() {

    const [queryParams] = useSearchParams();

    // Ana sayfadaki arama kutusu buraya ?search= ile yönlendiriyor.
    const [arama, setArama] = useState(() => queryParams.get("search") ?? "");

    const gecikmeliArama = useDebounce(arama);

    const [offset, setOffset] = useState(0);

    const { sayfa, yukleniyor, hata } = usePagedList(

        () => getProfessors({ search: gecikmeliArama.trim() || undefined, limit: LIMIT, offset }),

        [gecikmeliArama, offset]

    );


    const aramaDegisti = (deger) => {

        setArama(deger);

        setOffset(0);

    };


    return (

        <section className="max-w-[1200px] mx-auto px-6 py-16">

            <h1 className="heading-font text-5xl mb-10">

                Hocalar

            </h1>

            <input
                className="w-full max-w-[400px] border border-[#102744] p-3 mb-10"
                placeholder="Hoca ara"
                value={arama}
                onChange={(e) => aramaDegisti(e.target.value)}
            />

            {yukleniyor && <Loading />}

            <ErrorMessage message={hata} />

            {!yukleniyor && !hata && sayfa.items.length === 0 && (

                <p className="text-gray-600">

                    Aramanızla eşleşen hoca yok.

                </p>

            )}

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">

                {sayfa.items.map((hoca) => (

                    <Link key={hoca.id} to={`/hocalar/${hoca.id}`}>

                        <Card className="p-6 h-full">

                            <h2 className="text-xl font-semibold">

                                {hoca.title ? `${hoca.title} ` : ""}{hoca.full_name}

                            </h2>

                            <p className="text-gray-600 mt-2 text-sm">

                                {hoca.course_count} ders · {hoca.review_count} değerlendirme

                            </p>

                            {hoca.review_count === 0 ? (

                                <p className="mt-2 text-sm">

                                    henüz yorum yok

                                </p>

                            ) : (

                                <p className="mt-2 text-sm">

                                    Anlatım {hoca.average_teaching_score.toFixed(1)} ·
                                    Zorluk {hoca.average_difficulty_score.toFixed(1)} ·
                                    Adalet {hoca.average_fairness_score.toFixed(1)}

                                </p>

                            )}

                        </Card>

                    </Link>

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

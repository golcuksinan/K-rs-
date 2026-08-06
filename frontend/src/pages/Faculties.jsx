import { useState } from "react";

import { Link, useParams } from "react-router-dom";

import { getFaculties } from "../api/faculties";

import useDebounce from "../hooks/useDebounce";
import usePagedList from "../hooks/usePagedList";

import Card from "../components/Card";
import ErrorMessage from "../components/Error";
import Loading from "../components/Loading";
import Pagination from "../components/Pagination";


const LIMIT = 24;


export default function Faculties() {

    const { universityId } = useParams();

    const [arama, setArama] = useState("");

    const gecikmeliArama = useDebounce(arama);

    const [offset, setOffset] = useState(0);

    const { sayfa, yukleniyor, hata } = usePagedList(

        () => getFaculties({

            university_id: universityId,

            search: gecikmeliArama.trim() || undefined,

            limit: LIMIT,

            offset,

        }),

        [universityId, gecikmeliArama, offset]

    );


    const aramaDegisti = (deger) => {

        setArama(deger);

        setOffset(0);

    };


    return (

        <section className="max-w-[1200px] mx-auto px-6 py-16">

            <h1 className="heading-font text-5xl mb-4">

                Fakülteler

            </h1>

            <p className="mb-10">

                <Link to="/universiteler" className="underline">
                    Üniversite listesine dön
                </Link>

            </p>

            <input
                className="w-full max-w-[400px] border border-[#102744] p-3 mb-10"
                placeholder="Fakülte ara"
                value={arama}
                onChange={(e) => aramaDegisti(e.target.value)}
            />

            {yukleniyor && <Loading />}

            <ErrorMessage message={hata} />

            {!yukleniyor && !hata && sayfa.items.length === 0 && (

                <p className="text-gray-600">

                    Bu üniversitede listelenecek fakülte yok.

                </p>

            )}

            <div className="grid md:grid-cols-3 gap-6">

                {sayfa.items.map((fakulte) => (

                    <Link key={fakulte.id} to={`/fakulteler/${fakulte.id}/bolumler`}>

                        <Card className="p-6 h-full">

                            <h2 className="text-xl font-semibold">

                                {fakulte.name}

                            </h2>

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

import { useState } from "react";

import { Link } from "react-router-dom";

import { getUniversities } from "../api/universities";

import useDebounce from "../hooks/useDebounce";
import usePagedList from "../hooks/usePagedList";

import Card from "../components/Card";
import ErrorMessage from "../components/Error";
import Loading from "../components/Loading";
import Pagination from "../components/Pagination";


const LIMIT = 24;


export default function Universities() {

    const [arama, setArama] = useState("");

    const gecikmeliArama = useDebounce(arama);

    const [offset, setOffset] = useState(0);

    const { sayfa, yukleniyor, hata } = usePagedList(

        () => getUniversities({ search: gecikmeliArama.trim() || undefined, limit: LIMIT, offset }),

        [gecikmeliArama, offset]

    );


    const aramaDegisti = (deger) => {

        setArama(deger);

        setOffset(0);

    };


    return (

        <section className="max-w-[1200px] mx-auto px-6 py-16">

            <h1 className="heading-font text-5xl mb-10">

                Üniversiteler

            </h1>

            <input
                className="w-full max-w-[400px] border border-[#102744] p-3 mb-10"
                placeholder="Üniversite ara"
                value={arama}
                onChange={(e) => aramaDegisti(e.target.value)}
            />

            {yukleniyor && <Loading />}

            <ErrorMessage message={hata} />

            {!yukleniyor && !hata && sayfa.items.length === 0 && (

                <p className="text-gray-600">

                    Aramanızla eşleşen üniversite yok.

                </p>

            )}

            <div className="grid md:grid-cols-3 gap-6">

                {sayfa.items.map((universite) => (

                    <Link key={universite.id} to={`/universiteler/${universite.id}/fakulteler`}>

                        <Card className="p-6 h-full">

                            <h2 className="text-xl font-semibold">

                                {universite.name}

                            </h2>

                            <p className="text-gray-600 mt-2">

                                {universite.city}

                            </p>

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

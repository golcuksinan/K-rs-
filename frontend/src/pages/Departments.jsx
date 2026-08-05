import { useState } from "react";

import { Link, useParams } from "react-router-dom";

import { getDepartments } from "../api/departments";

import useDebounce from "../hooks/useDebounce";
import usePagedList from "../hooks/usePagedList";

import Card from "../components/Card";
import ErrorMessage from "../components/Error";
import Loading from "../components/Loading";
import Pagination from "../components/Pagination";


const LIMIT = 24;


export default function Departments() {

    const { facultyId } = useParams();

    const [arama, setArama] = useState("");

    const gecikmeliArama = useDebounce(arama);

    const [offset, setOffset] = useState(0);

    const [acikGrup, setAcikGrup] = useState("");

    const terim = gecikmeliArama.trim();

    // Fakülte verilirse düz liste, verilmezse ada göre gruplanmış liste döner; grup dalında
    // arama zorunlu (yoksa backend 422).
    const { sayfa, yukleniyor, hata } = usePagedList(

        () => getDepartments({

            faculty_id: facultyId,

            search: terim || undefined,

            limit: LIMIT,

            offset,

        }),

        [facultyId, terim, offset],

        !facultyId && !terim

    );

    const gruplu = !facultyId;


    const aramaDegisti = (deger) => {

        setArama(deger);

        setOffset(0);

    };


    return (

        <section className="max-w-[1200px] mx-auto px-6 py-16">

            <h1 className="heading-font text-5xl mb-4">

                Bölümler

            </h1>

            {facultyId && (

                <p className="mb-10">

                    <Link to="/universiteler" className="underline">
                        Üniversite listesine dön
                    </Link>

                </p>

            )}

            <input
                className="w-full max-w-[400px] border border-[#102744] p-3 mb-10"
                placeholder="Bölüm ara"
                value={arama}
                onChange={(e) => aramaDegisti(e.target.value)}
            />

            {yukleniyor && <Loading />}

            <ErrorMessage message={hata} />

            {gruplu && !terim && (

                <p className="text-gray-600">

                    Aramak istediğiniz bölümün adını yazın.

                </p>

            )}

            {!yukleniyor && !hata && (facultyId || terim) && sayfa.items.length === 0 && (

                <p className="text-gray-600">

                    Listelenecek bölüm yok.

                </p>

            )}

            {gruplu ? (

                <div className="space-y-4">

                    {terim && sayfa.items.map((grup) => (

                        <Card key={grup.department_name} className="p-6">

                            <button
                                className="text-xl font-semibold text-left w-full"
                                onClick={() => setAcikGrup(

                                    acikGrup === grup.department_name ? "" : grup.department_name

                                )}
                            >

                                {grup.department_name}

                                <span className="text-gray-600 text-base font-normal">

                                    {" "}({grup.faculties.length} fakülte)

                                </span>

                            </button>

                            {acikGrup === grup.department_name && (

                                <ul className="mt-4 space-y-2">

                                    {grup.faculties.map((fakulte) => (

                                        <li key={fakulte.id}>

                                            <Link
                                                to={`/fakulteler/${fakulte.id}/bolumler`}
                                                className="underline"
                                            >

                                                {fakulte.name}

                                            </Link>

                                        </li>

                                    ))}

                                </ul>

                            )}

                        </Card>

                    ))}

                </div>

            ) : (

                <div className="grid md:grid-cols-3 gap-6">

                    {sayfa.items.map((bolum) => (

                        <Card key={bolum.id} className="p-6 h-full">

                            <h2 className="text-xl font-semibold">

                                {bolum.name}

                            </h2>

                            <Link
                                to={`/dersler?department_id=${bolum.id}`}
                                className="underline text-sm"
                            >

                                Derslerini gör

                            </Link>

                        </Card>

                    ))}

                </div>

            )}

            <Pagination
                total={sayfa.total}
                limit={LIMIT}
                offset={offset}
                onChange={setOffset}
            />

        </section>

    );

}

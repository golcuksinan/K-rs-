import { useState } from "react";

import { Link, useSearchParams } from "react-router-dom";

import { getCourses } from "../../api/courses";

import useDebounce from "../../hooks/useDebounce";
import usePagedList from "../../hooks/usePagedList";

import Card from "../../components/Card";
import ErrorMessage from "../../components/Error";
import Loading from "../../components/Loading";
import Pagination from "../../components/Pagination";


const LIMIT = 24;

const MIN_ARAMA = 2;


export default function Courses() {

    const [queryParams] = useSearchParams();

    const departmentId = queryParams.get("department_id");

    // Ana sayfadaki arama kutusu buraya ?search= ile yönlendiriyor.
    const [arama, setArama] = useState(() => queryParams.get("search") ?? "");

    const gecikmeliArama = useDebounce(arama);

    const [offset, setOffset] = useState(0);

    const terim = gecikmeliArama.trim();

    // department_id yoksa en az 2 karakterlik arama zorunlu (yoksa backend 422).
    const aramaYeterli = terim.length >= MIN_ARAMA;

    const { sayfa, yukleniyor, hata } = usePagedList(

        () => getCourses({

            department_id: departmentId || undefined,

            search: aramaYeterli ? terim : undefined,

            limit: LIMIT,

            offset,

        }),

        [departmentId, aramaYeterli ? terim : "", offset],

        !departmentId && !aramaYeterli

    );

    const listeVar = Boolean(departmentId) || aramaYeterli;


    const aramaDegisti = (deger) => {

        setArama(deger);

        setOffset(0);

    };


    return (

        <section className="max-w-[1200px] mx-auto px-6 py-16">

            <h1 className="heading-font text-5xl mb-10">

                Dersler

            </h1>

            <input
                className="w-full max-w-[400px] border border-[#102744] p-3 mb-10"
                placeholder="Ders adı veya kodu ara"
                value={arama}
                onChange={(e) => aramaDegisti(e.target.value)}
            />

            {yukleniyor && <Loading />}

            <ErrorMessage message={hata} />

            {!listeVar && (

                <p className="text-gray-600">

                    Aramak istediğiniz dersin adını ya da kodunu yazın (en az {MIN_ARAMA} karakter),
                    ya da{" "}

                    <Link to="/bolumler" className="underline">
                        bölüm seçerek
                    </Link>

                    {" "}ilerleyin.

                </p>

            )}

            {listeVar && !yukleniyor && !hata && sayfa.items.length === 0 && (

                <p className="text-gray-600">

                    Listelenecek ders yok.

                </p>

            )}

            {listeVar && (

                <div className="grid md:grid-cols-3 gap-6">

                    {/* Ders detay ucu olmadığı için ad/kod detay sayfasına state ile taşınıyor. */}
                    {sayfa.items.map((ders) => (

                        <Link
                            key={ders.id}
                            to={`/dersler/${ders.id}`}
                            state={{ ders: { name: ders.name, code: ders.code } }}
                        >

                            <Card className={`p-6 h-full ${ders.professor_count === 0 ? "opacity-60" : ""}`}>

                                <h2 className="text-xl font-semibold">

                                    {ders.name}

                                </h2>

                                <p className="text-gray-600 mt-2">

                                    {ders.code} · {ders.university_short_name || ders.university_name}

                                </p>

                                {/* Bölüm/müfredat alanları yalnızca department_id dalında dolu. */}
                                {ders.department_name && (

                                    <p className="text-gray-600 mt-1 text-sm">

                                        {ders.department_name}

                                        {ders.is_elective === true && " · seçmeli"}

                                        {ders.is_elective === false && " · zorunlu"}

                                    </p>

                                )}

                                {ders.professor_count === 0 && (

                                    <p className="mt-2 text-sm">

                                        hoca kaydı yok

                                    </p>

                                )}

                            </Card>

                        </Link>

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

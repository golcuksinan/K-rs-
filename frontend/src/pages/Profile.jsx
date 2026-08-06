import { useContext } from "react";

import { Link } from "react-router-dom";

import { AuthContext } from "../context/auth-context";

import Card from "../components/Card";


// Sınıf enrollment_year'dan hesaplanıp int olarak dönüyor; 0 hazırlık demek.
const sinifYazisi = (sinif) => (sinif === 0 ? "Hazırlık" : `${sinif}. sınıf`);


export default function Profile() {

    const { user, logout } = useContext(AuthContext);

    if (!user) {

        return null;

    }

    // E-posta ve isim hiçbir yanıtta dönmüyor (anonimlik); gösterilecek alanlar bunlar.
    const satirlar = [

        ["Üniversite", user.university_short_name || user.university_name],

        ["Fakülte", user.faculty_name],

        ["Bölüm", user.department_name],

        ["Sınıf", sinifYazisi(user.current_grade)],

        ["Kayıt yılı", user.enrollment_year],

        ["E-posta doğrulaması", user.is_verified ? "Tamamlandı" : "bekliyor"],

    ];

    return (

        <section className="max-w-[1000px] mx-auto px-6 py-16">

            <h1 className="heading-font text-5xl mb-10">

                Profil

            </h1>

            <Card className="p-8">

                <dl className="space-y-3">

                    {satirlar.map(([etiket, deger]) => (

                        <div key={etiket} className="flex justify-between gap-6">

                            <dt className="text-gray-600">

                                {etiket}

                            </dt>

                            <dd>

                                {deger}

                            </dd>

                        </div>

                    ))}

                </dl>

                {user.role === "admin" && (

                    <p className="mt-6">

                        <Link to="/admin/moderasyon" className="underline">

                            Admin paneli

                        </Link>

                    </p>

                )}

                <p className="mt-6">

                    <Link to="/yorumlarim" className="underline">

                        Yorumlarım

                    </Link>

                </p>

                <button

                    onClick={logout}

                    className="mt-8 bg-[#102744] text-white px-6 py-3"

                >

                    Çıkış Yap

                </button>

            </Card>

        </section>

    );

}

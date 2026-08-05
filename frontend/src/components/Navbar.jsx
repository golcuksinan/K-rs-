import { useContext, useState } from "react";

import { Link } from "react-router-dom";

import { AuthContext } from "../context/auth-context";


export default function Navbar() {

    const { user, logout } = useContext(AuthContext);

    const [open, setOpen] = useState(false);

    const baglantilar = [

        ["/hocalar", "Hocalar"],

        ["/dersler", "Dersler"],

        ["/bolumler", "Bölümler"],

        ["/universiteler", "Üniversiteler"],

    ];

    if (user) {

        baglantilar.push(["/yorumlarim", "Yorumlarım"]);

    }

    if (user?.role === "admin") {

        baglantilar.push(["/admin/moderasyon", "Admin"]);

    }

    return (

        <header className="max-w-[1200px] mx-auto px-6 py-6">

            <div className="flex justify-between items-center">

                <Link to="/" className="text-3xl font-bold">

                    KÜRSÜ

                </Link>

                <button className="md:hidden text-2xl" onClick={() => setOpen(!open)}>

                    ☰

                </button>

                <nav className="hidden md:flex gap-8 items-center">

                    {baglantilar.map(([yol, etiket]) => (

                        <Link key={yol} to={yol}>

                            {etiket}

                        </Link>

                    ))}

                    {user ? (

                        <>

                            <Link to="/profil" className="border px-5 py-2">

                                Profil

                            </Link>

                            <button onClick={logout} className="bg-[#102744] text-white px-5 py-2">

                                Çıkış

                            </button>

                        </>

                    ) : (

                        <>

                            <Link to="/giris" className="border px-5 py-2">

                                Giriş

                            </Link>

                            <Link to="/kayit" className="bg-[#102744] text-white px-5 py-2">

                                Kayıt

                            </Link>

                        </>

                    )}

                </nav>

            </div>

            {open && (

                <div className="md:hidden mt-6 flex flex-col gap-5 border-t pt-5">

                    {baglantilar.map(([yol, etiket]) => (

                        <Link key={yol} to={yol} onClick={() => setOpen(false)}>

                            {etiket}

                        </Link>

                    ))}

                    {user ? (

                        <>

                            <Link to="/profil" onClick={() => setOpen(false)}>

                                Profil

                            </Link>

                            <button className="text-left" onClick={logout}>

                                Çıkış

                            </button>

                        </>

                    ) : (

                        <>

                            <Link to="/giris" onClick={() => setOpen(false)}>

                                Giriş

                            </Link>

                            <Link to="/kayit" onClick={() => setOpen(false)}>

                                Kayıt

                            </Link>

                        </>

                    )}

                </div>

            )}

        </header>

    );

}

import { useState } from "react";

import { useLocation, useNavigate } from "react-router-dom";

import { resetPassword } from "../../api/auth";

import parseError from "../../api/parseError";

import ErrorMessage from "../../components/Error";


export default function ResetPassword() {

    const navigate = useNavigate();

    const location = useLocation();

    const [form, setForm] = useState({

        email: location.state?.email ?? "",

        otp: "",

        new_password: "",

    });

    const [hata, setHata] = useState("");

    const [gonderiliyor, setGonderiliyor] = useState(false);


    const submit = (e) => {

        e.preventDefault();

        setHata("");

        setGonderiliyor(true);

        resetPassword(form)

            .then(() => navigate("/giris"))

            .catch((error) => setHata(parseError(error)))

            .finally(() => setGonderiliyor(false));

    };


    return (

        <div className="max-w-md mx-auto px-6 py-20">

            <h1 className="heading-font text-4xl mb-8">

                Şifre Sıfırla

            </h1>

            <form onSubmit={submit} className="space-y-5">

                <input
                    className="w-full border p-3"
                    placeholder="E-posta"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                />

                <input
                    className="w-full border p-3"
                    placeholder="Sıfırlama kodu"
                    maxLength={6}
                    value={form.otp}
                    onChange={(e) => setForm({ ...form, otp: e.target.value })}
                />

                <input
                    type="password"
                    className="w-full border p-3"
                    placeholder="Yeni şifre (en az 8 karakter, bir rakam)"
                    value={form.new_password}
                    onChange={(e) => setForm({ ...form, new_password: e.target.value })}
                />

                <button
                    className="bg-[#102744] text-white w-full py-3 disabled:opacity-60"
                    disabled={gonderiliyor}
                >

                    Şifreyi Güncelle

                </button>

            </form>

            <ErrorMessage message={hata} />

        </div>

    );

}

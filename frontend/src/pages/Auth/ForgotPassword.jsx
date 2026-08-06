import { useState } from "react";

import { useNavigate } from "react-router-dom";

import { forgotPassword } from "../../api/auth";

import parseError from "../../api/parseError";

import ErrorMessage from "../../components/Error";


export default function ForgotPassword() {

    const navigate = useNavigate();

    const [email, setEmail] = useState("");

    const [hata, setHata] = useState("");

    const [gonderiliyor, setGonderiliyor] = useState(false);


    const submit = (e) => {

        e.preventDefault();

        setHata("");

        setGonderiliyor(true);

        forgotPassword({ email })

            // Adres kayıtlı olmasa da aynı yanıt döner; ayrım yapılmadan sıfırlama ekranına geçilir.
            .then(() => navigate("/sifre-sifirla", { state: { email } }))

            .catch((error) => setHata(parseError(error)))

            .finally(() => setGonderiliyor(false));

    };


    return (

        <div className="max-w-md mx-auto px-6 py-20">

            <h1 className="heading-font text-4xl mb-4">

                Şifremi Unuttum

            </h1>

            <p className="mb-8 text-gray-600">

                E-posta adresinize sıfırlama kodu gönderilecek.

            </p>

            <form onSubmit={submit} className="space-y-5">

                <input
                    className="w-full border p-3"
                    placeholder="E-posta"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                />

                <button
                    className="bg-[#102744] text-white w-full py-3 disabled:opacity-60"
                    disabled={gonderiliyor}
                >

                    Kod Gönder

                </button>

            </form>

            <ErrorMessage message={hata} />

        </div>

    );

}

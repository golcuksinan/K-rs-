import { useContext, useState } from "react";

import { Link, useLocation, useNavigate } from "react-router-dom";

import { verifyOtp } from "../../api/auth";

import parseError from "../../api/parseError";

import ErrorMessage from "../../components/Error";

import { AuthContext } from "../../context/auth-context";


export default function VerifyOtp() {

    const { login } = useContext(AuthContext);

    const navigate = useNavigate();

    const location = useLocation();

    // Sayfa yenilenirse router state'i kaybolur, e-posta elle girilebilsin.
    const [email, setEmail] = useState(location.state?.email ?? "");

    const [otp, setOtp] = useState("");

    const [hata, setHata] = useState("");

    const [gonderiliyor, setGonderiliyor] = useState(false);


    const submit = (e) => {

        e.preventDefault();

        setHata("");

        setGonderiliyor(true);

        verifyOtp({ email, otp })

            .then((res) => login(res.data.access_token))

            .then(() => navigate("/"))

            .catch((error) => setHata(parseError(error)))

            .finally(() => setGonderiliyor(false));

    };


    return (

        <div className="max-w-md mx-auto px-6 py-20">

            <h1 className="heading-font text-4xl mb-4">

                E-postanı Doğrula

            </h1>

            <p className="mb-8 text-gray-600">

                Adresinize gönderilen 6 haneli kodu girin.

            </p>

            <form onSubmit={submit} className="space-y-5">

                <input
                    className="w-full border p-3"
                    placeholder="E-posta"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                />

                <input
                    className="w-full border p-3"
                    placeholder="Doğrulama kodu"
                    maxLength={6}
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                />

                <button
                    className="bg-[#102744] text-white w-full py-3 disabled:opacity-60"
                    disabled={gonderiliyor}
                >

                    Doğrula

                </button>

            </form>

            <ErrorMessage message={hata} />

            {hata.includes("kayıt olun") && (

                <p className="text-center">

                    <Link to="/kayit" className="underline">
                        Kayıt ekranına dön
                    </Link>

                </p>

            )}

        </div>

    );

}

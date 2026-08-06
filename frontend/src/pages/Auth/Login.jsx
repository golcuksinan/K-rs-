import { useState, useContext } from "react";

import { Link, useNavigate } from "react-router-dom";

import { loginUser } from "../../api/auth";

import parseError from "../../api/parseError";

import ErrorMessage from "../../components/Error";

import { AuthContext } from "../../context/auth-context";


export default function Login() {

    const { login } = useContext(AuthContext);

    const navigate = useNavigate();

    const [form, setForm] = useState({ email: "", password: "" });

    const [hata, setHata] = useState("");

    const [gonderiliyor, setGonderiliyor] = useState(false);


    const submit = (e) => {

        e.preventDefault();

        setHata("");

        setGonderiliyor(true);

        loginUser(form)

            .then((res) => login(res.data.access_token))

            // Tam sayfa yenilemesi context'i sıfırlıyor, yönlendirme router üzerinden.
            .then(() => navigate("/"))

            .catch((error) => setHata(parseError(error)))

            .finally(() => setGonderiliyor(false));

    };


    return (

        <div className="max-w-md mx-auto px-6 py-20">

            <h1 className="heading-font text-4xl mb-8">

                Giriş

            </h1>

            <form onSubmit={submit} className="space-y-5">

                <input

                    className="w-full border p-3"

                    placeholder="E-posta"

                    value={form.email}

                    onChange={(e) => setForm({ ...form, email: e.target.value })}

                />

                <input

                    type="password"

                    className="w-full border p-3"

                    placeholder="Şifre"

                    value={form.password}

                    onChange={(e) => setForm({ ...form, password: e.target.value })}

                />

                <button

                    className="bg-[#102744] text-white w-full py-3 disabled:opacity-60"

                    disabled={gonderiliyor}

                >

                    Giriş Yap

                </button>

            </form>

            <ErrorMessage message={hata} />

            <p className="text-center mt-6">

                <Link to="/sifremi-unuttum" className="underline">
                    Şifremi unuttum
                </Link>

            </p>

            <p className="text-center mt-3">

                Hesabın yok mu?{" "}

                <Link to="/kayit" className="underline">
                    Kayıt ol
                </Link>

            </p>

        </div>

    );

}

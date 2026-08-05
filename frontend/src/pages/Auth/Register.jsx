import { useEffect, useState } from "react";

import { useNavigate } from "react-router-dom";

import { registerUser } from "../../api/auth";

import { getUniversities } from "../../api/universities";

import { getFaculties } from "../../api/faculties";

import { getDepartments } from "../../api/departments";

import parseError from "../../api/parseError";

import ErrorMessage from "../../components/Error";


export default function Register() {

    const navigate = useNavigate();

    const [form, setForm] = useState({ email: "", password: "", enrollment_year: "" });

    const [universiteAra, setUniversiteAra] = useState("");

    const [universiteler, setUniversiteler] = useState([]);

    const [universiteId, setUniversiteId] = useState("");

    const [fakulteler, setFakulteler] = useState([]);

    const [fakulteId, setFakulteId] = useState("");

    const [bolumler, setBolumler] = useState([]);

    const [bolumId, setBolumId] = useState("");

    const [hata, setHata] = useState("");

    const [gonderiliyor, setGonderiliyor] = useState(false);


    // Her tuşta istek atılmaz: global limit 20/second ve dev'de StrictMode effect'i ikiye katlıyor.
    useEffect(() => {

        const zamanlayici = setTimeout(() => {

            getUniversities({ search: universiteAra.trim() || undefined, limit: 20 })

                .then((res) => setUniversiteler(res.data.items))

                .catch(() => setUniversiteler([]));

        }, 300);

        return () => clearTimeout(zamanlayici);

    }, [universiteAra]);


    useEffect(() => {

        if (!universiteId) {

            return;

        }

        getFaculties({ university_id: universiteId, limit: 100 })

            .then((res) => setFakulteler(res.data.items))

            .catch(() => setFakulteler([]));

    }, [universiteId]);


    useEffect(() => {

        if (!fakulteId) {

            return;

        }

        getDepartments({ faculty_id: fakulteId, limit: 100 })

            .then((res) => setBolumler(res.data.items))

            .catch(() => setBolumler([]));

    }, [fakulteId]);


    // Alt seçimler effect'te değil burada sıfırlanır: effect gövdesinde setState
    // cascading render'a yol açıyor (react-hooks/set-state-in-effect).
    const universiteSec = (id) => {

        setUniversiteId(id);

        setFakulteId("");

        setFakulteler([]);

        setBolumId("");

        setBolumler([]);

    };


    const fakulteSec = (id) => {

        setFakulteId(id);

        setBolumId("");

        setBolumler([]);

    };


    const submit = (e) => {

        e.preventDefault();

        setHata("");

        if (!bolumId) {

            setHata("Bölümünüzü seçin");

            return;

        }

        setGonderiliyor(true);

        registerUser({

            email: form.email,

            password: form.password,

            department_id: Number(bolumId),

            enrollment_year: Number(form.enrollment_year),

        })

            // Yanıt token değil mesaj; e-posta kayıtlı olsa da aynı mesaj döner.
            .then(() => navigate("/kayit/dogrula", { state: { email: form.email } }))

            .catch((error) => setHata(parseError(error)))

            .finally(() => setGonderiliyor(false));

    };


    return (

        <div className="max-w-md mx-auto px-6 py-20">

            <h1 className="heading-font text-4xl mb-8">

                Kayıt Ol

            </h1>

            <form onSubmit={submit} className="space-y-5">

                <input
                    className="w-full border p-3"
                    placeholder="E-posta (.edu.tr)"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                />

                <input
                    type="password"
                    className="w-full border p-3"
                    placeholder="Şifre (en az 8 karakter, bir rakam)"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                />

                <input
                    type="number"
                    className="w-full border p-3"
                    placeholder="Üniversiteye giriş yılı"
                    value={form.enrollment_year}
                    onChange={(e) => setForm({ ...form, enrollment_year: e.target.value })}
                />

                <input
                    className="w-full border p-3"
                    placeholder="Üniversite ara"
                    value={universiteAra}
                    onChange={(e) => setUniversiteAra(e.target.value)}
                />

                <select
                    className="w-full border p-3"
                    value={universiteId}
                    onChange={(e) => universiteSec(e.target.value)}
                >

                    <option value="">Üniversite seçin</option>

                    {universiteler.map((universite) => (

                        <option key={universite.id} value={universite.id}>
                            {universite.name}
                        </option>

                    ))}

                </select>

                <select
                    className="w-full border p-3 disabled:opacity-60"
                    value={fakulteId}
                    disabled={!universiteId}
                    onChange={(e) => fakulteSec(e.target.value)}
                >

                    <option value="">Fakülte seçin</option>

                    {fakulteler.map((fakulte) => (

                        <option key={fakulte.id} value={fakulte.id}>
                            {fakulte.name}
                        </option>

                    ))}

                </select>

                <select
                    className="w-full border p-3 disabled:opacity-60"
                    value={bolumId}
                    disabled={!fakulteId}
                    onChange={(e) => setBolumId(e.target.value)}
                >

                    <option value="">Bölüm seçin</option>

                    {bolumler.map((bolum) => (

                        <option key={bolum.id} value={bolum.id}>
                            {bolum.name}
                        </option>

                    ))}

                </select>

                <button
                    className="bg-[#102744] text-white w-full py-3 disabled:opacity-60"
                    disabled={gonderiliyor}
                >

                    Kayıt Ol

                </button>

            </form>

            <ErrorMessage message={hata} />

        </div>

    );

}

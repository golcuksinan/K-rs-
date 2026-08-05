import { useState } from "react";

import { useNavigate } from "react-router-dom";

import { Search } from "lucide-react";


export default function SearchBar() {

    const navigate = useNavigate();

    const [terim, setTerim] = useState("");

    const [tur, setTur] = useState("dersler");


    const submit = (e) => {

        e.preventDefault();

        const temiz = terim.trim();

        if (!temiz) {

            return;

        }

        navigate(`/${tur}?search=${encodeURIComponent(temiz)}`);

    };


    return (

        <form
            onSubmit={submit}
            className="flex w-full max-w-[600px] border border-[#102744] bg-white"
        >

            <div className="flex items-center gap-3 px-5 flex-1">

                <Search size={20} />

                <input
                    type="text"
                    placeholder="Hoca veya ders ara..."
                    className="outline-none w-full bg-transparent text-sm"
                    value={terim}
                    onChange={(e) => setTerim(e.target.value)}
                />

            </div>

            <select
                className="border-l border-[#102744] px-3 text-sm bg-transparent"
                value={tur}
                onChange={(e) => setTur(e.target.value)}
            >

                <option value="dersler">Ders</option>

                <option value="hocalar">Hoca</option>

            </select>

            <button className="bg-[#102744] text-white px-8 text-sm">

                Ara

            </button>

        </form>

    );

}

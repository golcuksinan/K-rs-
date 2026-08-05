import { NavLink } from "react-router-dom";


const BAGLANTILAR = [

    ["/admin/moderasyon", "Moderasyon"],

    ["/admin/raporlar", "Raporlar"],

    ["/admin/istatistikler", "İstatistikler"],

];


export default function AdminNav() {

    return (

        <nav className="flex gap-6 mb-10 border-b pb-4">

            {BAGLANTILAR.map(([yol, etiket]) => (

                <NavLink
                    key={yol}
                    to={yol}
                    className={({ isActive }) => (isActive ? "font-semibold" : "text-gray-600")}
                >

                    {etiket}

                </NavLink>

            ))}

        </nav>

    );

}

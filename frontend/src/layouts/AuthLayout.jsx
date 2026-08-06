import { Link, Outlet } from "react-router-dom";

import BackButton from "../components/BackButton";
import { authBackground } from "../config/pageBackgrounds";


export default function AuthLayout() {

    return (

        <div className="relative min-h-screen overflow-hidden">

            <div
                className="absolute inset-0 bg-cover bg-center bg-no-repeat"
                style={{ backgroundImage: `url(${authBackground})` }}
            ></div>

            <div className="absolute inset-0 bg-[#F8F2E8]/80"></div>

            <div className="relative z-10">

                <header className="max-w-[1200px] mx-auto px-6 py-6 flex items-center gap-6">

                    <Link to="/" className="text-3xl font-bold">

                        KÜRSÜ

                    </Link>

                    <BackButton />

                </header>

                <main>

                    <Outlet />

                </main>

            </div>

        </div>

    );

}
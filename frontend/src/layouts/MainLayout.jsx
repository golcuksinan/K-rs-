import { Outlet, useLocation } from "react-router-dom";

import BackButton from "../components/BackButton";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import { getPageBackground } from "../config/pageBackgrounds";


export default function MainLayout(){


const { pathname } = useLocation();

const backgroundImage = getPageBackground(pathname);


return (

<div

className="
relative
min-h-screen
overflow-hidden
"

>


<div

className="absolute inset-0 bg-cover bg-bottom bg-no-repeat"
style={{ backgroundImage: `url(${backgroundImage})` }}

></div>


<div

className="
absolute
inset-0
bg-[#F8F2E8]/10
"

></div>



<div

className="
relative
z-10
"

>


<Navbar />


{pathname !== "/" && (

<div

className="
max-w-[1200px]
mx-auto
px-6
"

>

<BackButton/>

</div>

)}


<main>

<Outlet />

</main>


<Footer />


</div>


</div>

);

}
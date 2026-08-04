import { Outlet } from "react-router-dom";

import Navbar from "../components/Navbar";
import Footer from "../components/Footer";


export default function MainLayout(){


return (

<div

className="
relative
min-h-screen
overflow-hidden
"

>


<div

className="
absolute
inset-0
bg-[#F8F2E8]/80
"

></div>



<div

className="
relative
z-10
"

>


<Navbar />


<main>

<Outlet />

</main>


<Footer />


</div>


</div>

);

}
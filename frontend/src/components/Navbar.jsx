import {
Link
} from "react-router-dom";


import {
useState
} from "react";


export default function Navbar(){


const [open,setOpen]=useState(false);



return (

<header

className="
max-w-[1200px]
mx-auto
px-6
py-6
"

>


<div

className="
flex
justify-between
items-center
"

>


<Link

to="/"

className="
text-3xl
font-bold
"

>

KÜRSÜ

</Link>



<button

className="
md:hidden
text-2xl
"

onClick={()=>setOpen(!open)}

>

☰

</button>



<nav

className="
hidden
md:flex
gap-8
items-center
"

>


<Link to="/hocalar">

Hocalar

</Link>


<Link to="/dersler">

Dersler

</Link>


<Link to="/bolumler">

Bölümler

</Link>


<Link to="/universiteler">

Üniversiteler

</Link>



<Link

to="/giris"

className="
border
px-5
py-2
"

>

Giriş

</Link>



<Link

to="/kayit"

className="
bg-[#102744]
text-white
px-5
py-2
"

>

Kayıt

</Link>



</nav>


</div>



{

open &&

<div

className="
md:hidden
mt-6
flex
flex-col
gap-5
border-t
pt-5
"

>


<Link to="/hocalar">

Hocalar

</Link>


<Link to="/dersler">

Dersler

</Link>


<Link to="/bolumler">

Bölümler

</Link>


<Link to="/universiteler">

Üniversiteler

</Link>


<Link to="/giris">

Giriş

</Link>


<Link to="/kayit">

Kayıt

</Link>


</div>


}


</header>

);

}
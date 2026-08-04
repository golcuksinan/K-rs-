import {
useContext
} from "react";


import {
AuthContext
} from "../context/auth-context";


import Card from "../components/Card";


export default function Profile(){


const {
user,
logout
}=useContext(AuthContext);



return (

<section

className="
max-w-[1000px]
mx-auto
px-6
py-16
"

>


<h1

className="
heading-font
text-5xl
mb-10
"

>

Profil

</h1>



<Card

className="
p-8
"

>


<h2

className="
text-2xl
font-semibold
"

>

{user?.name}

</h2>



<p className="mt-3">

{user?.email}

</p>



<button

onClick={logout}

className="
mt-8
bg-[#102744]
text-white
px-6
py-3
"

>

Çıkış Yap

</button>



</Card>



</section>

);


}
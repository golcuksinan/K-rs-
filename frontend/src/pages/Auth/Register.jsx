import {
useState
} from "react";


import {
registerUser
} from "../../api/auth";


export default function Register(){


const [form,setForm]=useState({

name:"",
email:"",
password:""

});



const submit=(e)=>{

e.preventDefault();


registerUser(form)

.then(()=>{

window.location="/giris";

});


};



return (

<div className="
max-w-md
mx-auto
px-6
py-20
">


<h1 className="
heading-font
text-4xl
mb-8
">

Kayıt Ol

</h1>



<form

onSubmit={submit}

className="
space-y-5
"

>


<input
className="w-full border p-3"
placeholder="Ad Soyad"

onChange={(e)=>

setForm({

...form,

name:e.target.value

})

}

/>


<input
className="w-full border p-3"
placeholder="Email"

onChange={(e)=>

setForm({

...form,

email:e.target.value

})

}

/>


<input
type="password"

className="w-full border p-3"
placeholder="Şifre"

onChange={(e)=>

setForm({

...form,

password:e.target.value

})

}

/>


<button

className="
bg-[#102744]
text-white
w-full
py-3
"

>

Kayıt Ol

</button>


</form>


</div>

);

}
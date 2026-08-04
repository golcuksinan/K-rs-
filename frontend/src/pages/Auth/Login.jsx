import {
useState,
useContext
} from "react";

import {
loginUser
} from "../../api/auth";


import {
AuthContext
} from "../../context/auth-context";


export default function Login(){


const {login}=useContext(AuthContext);



const [form,setForm]=useState({

email:"",
password:""

});



const submit=(e)=>{

e.preventDefault();


loginUser(form)

.then(res=>{

login(res.data);

window.location="/";

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

Giriş

</h1>



<form

onSubmit={submit}

className="
space-y-5
"

>


<input

className="
w-full
border
p-3
"

placeholder="E-posta"

onChange={(e)=>

setForm({

...form,

email:e.target.value

})

}

/>



<input

type="password"

className="
w-full
border
p-3
"

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

Giriş Yap

</button>


</form>


</div>

);

}
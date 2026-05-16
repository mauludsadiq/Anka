# Running the Full Stack Demo

The full stack demo lives in Raqib and proves all four layers together:
Bay2, ANKA, Dalil, and Raqib in one script.

    git clone https://github.com/mauludsadiq/Bay2
    git clone https://github.com/mauludsadiq/Anka
    git clone https://github.com/mauludsadiq/Dalil
    git clone https://github.com/mauludsadiq/Raqib

    cd Raqib
    bash stack_demo.sh

Expected output: 12 verified steps. All layers green.

    Bay2      object_count=2  op_count=2
    ANKA      Oxford + MIT nodes, 2 claims converged via gossip
    Dalil     winner="3.4C per doubling of CO2"  score=1  cite_as=anka:sha256:...
    Raqib     unseen -> witnessed (Oxford claim)
    Compute   execution receipt in Bay2
    Recovery  both claims fetchable after restart

    Stack demo complete. All layers verified.

Full documentation: https://github.com/mauludsadiq/stack-pilot
